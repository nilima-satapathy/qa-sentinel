#!/usr/bin/env python3
"""
CI smoke: gate a golden subset offline (no network).

Usage:
  python scripts/run_batch_gate.py
  python scripts/run_batch_gate.py --limit 5
  python scripts/run_batch_gate.py --ids qa-001,qa-002

Exit 0 if all gated PASS or WARN; exit 1 if any FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qasentinel.chat_client import ChatClient  # noqa: E402
from qasentinel.paths import ensure_import_paths, eval_root  # noqa: E402
from qasentinel.quality_gate import evaluate_answer  # noqa: E402


def load_cases(ids: list[str] | None, limit: int) -> list[dict]:
    ensure_import_paths()
    path = eval_root() / "golden_dataset" / "qa_pairs.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = list(data.get("cases") or [])
    if ids:
        want = set(ids)
        cases = [c for c in cases if c.get("id") in want]
    return cases[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch golden quality-gate smoke")
    parser.add_argument("--limit", type=int, default=8, help="Max golden cases")
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated case ids (optional)",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Treat WARN as failure (default: only FAIL fails CI)",
    )
    args = parser.parse_args()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or None

    cases = load_cases(ids, args.limit)
    if not cases:
        print("ERROR: no golden cases loaded", file=sys.stderr)
        return 2

    client = ChatClient(api_key="")
    client.api_key = ""

    rows: list[dict] = []
    fails = 0
    warns = 0
    for case in cases:
        q = case["question"]
        # Prefer reference_answer as SUT output (offline golden path)
        resp = client.complete(q)
        answer = resp.answer if resp.backend == "golden" else case.get("reference_answer", "")
        gate = evaluate_answer(q, answer, use_judge=False)
        row = {
            "id": case.get("id"),
            "status": gate.status,
            "backend": resp.backend,
            "reasons": gate.reasons[:3],
        }
        rows.append(row)
        if gate.status == "FAIL":
            fails += 1
        elif gate.status == "WARN":
            warns += 1
        mark = {"PASS": "OK", "WARN": "WN", "FAIL": "FL"}[gate.status]
        print(f"[{mark}] {case.get('id')}: {gate.status}")
        for r in gate.reasons[:2]:
            print(f"       - {r}")

    print("---")
    print(f"Total={len(rows)} PASS={sum(1 for r in rows if r['status']=='PASS')} "
          f"WARN={warns} FAIL={fails}")

    if fails:
        print("BATCH GATE: FAILED")
        return 1
    if args.fail_on_warn and warns:
        print("BATCH GATE: FAILED (warns)")
        return 1
    print("BATCH GATE: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
