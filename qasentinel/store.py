"""SQLite turn history + free-tier usage tracking."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from qasentinel.paths import ROOT

DEFAULT_DB = ROOT / "data" / "turns.sqlite3"


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TurnStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    gate_status TEXT NOT NULL,
                    scores_json TEXT,
                    reasons_json TEXT,
                    latency_ms REAL,
                    total_tokens INTEGER,
                    model TEXT,
                    backend TEXT,
                    golden_case_id TEXT
                );
                CREATE TABLE IF NOT EXISTS usage_daily (
                    day TEXT PRIMARY KEY,
                    tokens INTEGER NOT NULL DEFAULT 0,
                    requests INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def add_turn(
        self,
        *,
        question: str,
        answer: str,
        gate_status: str,
        scores: dict[str, Any],
        reasons: list[str],
        latency_ms: float,
        total_tokens: int | None,
        model: str,
        backend: str,
        golden_case_id: str | None = None,
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO turns (
                    created_at, question, answer, gate_status, scores_json,
                    reasons_json, latency_ms, total_tokens, model, backend, golden_case_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    question,
                    answer,
                    gate_status,
                    json.dumps(scores),
                    json.dumps(reasons),
                    latency_ms,
                    total_tokens,
                    model,
                    backend,
                    golden_case_id,
                ),
            )
            return int(cur.lastrowid)

    def list_turns(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM turns ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def session_stats(self, limit: int = 100) -> dict[str, int]:
        turns = self.list_turns(limit=limit)
        total = len(turns)
        passed = sum(1 for t in turns if t["gate_status"] == "PASS")
        warn = sum(1 for t in turns if t["gate_status"] == "WARN")
        failed = sum(1 for t in turns if t["gate_status"] == "FAIL")
        return {"total": total, "pass": passed, "warn": warn, "fail": failed}

    def add_usage(self, tokens: int | None, requests: int = 1) -> None:
        day = _utc_today()
        tok = int(tokens or 0)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT tokens, requests FROM usage_daily WHERE day = ?", (day,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE usage_daily SET tokens = ?, requests = ? WHERE day = ?",
                    (int(row["tokens"]) + tok, int(row["requests"]) + requests, day),
                )
            else:
                conn.execute(
                    "INSERT INTO usage_daily (day, tokens, requests) VALUES (?, ?, ?)",
                    (day, tok, requests),
                )

    def usage_today(self) -> dict[str, int]:
        day = _utc_today()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT tokens, requests FROM usage_daily WHERE day = ?", (day,)
            ).fetchone()
            if not row:
                return {"tokens": 0, "requests": 0}
            return {"tokens": int(row["tokens"]), "requests": int(row["requests"])}

    def free_tier_snapshot(self, policy: dict[str, Any]) -> dict[str, Any]:
        used = self.usage_today()
        daily_tok = int(
            policy.get("free_tier_daily_tokens")
            or os.getenv("FREE_TIER_DAILY_TOKENS")
            or 500_000
        )
        daily_req = int(
            policy.get("free_tier_daily_requests")
            or os.getenv("FREE_TIER_DAILY_REQUESTS")
            or 14_400
        )
        rem_tok = max(0, daily_tok - used["tokens"])
        rem_req = max(0, daily_req - used["requests"])
        return {
            "tokens_used": used["tokens"],
            "tokens_limit": daily_tok,
            "tokens_remaining": rem_tok,
            "requests_used": used["requests"],
            "requests_limit": daily_req,
            "requests_remaining": rem_req,
            "frac_tokens_left": rem_tok / daily_tok if daily_tok else 0,
        }

    def export_csv(self, path: Path | None = None) -> Path:
        out = path or (ROOT / "reports" / f"turns_{_utc_today()}.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = self.list_turns(limit=1000)
        if not rows:
            out.write_text("id,created_at,gate_status\n", encoding="utf-8")
            return out
        fields = list(rows[0].keys())
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return out
