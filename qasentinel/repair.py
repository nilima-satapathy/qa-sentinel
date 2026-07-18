"""One-shot repair loop: rewrite a WARN/FAIL answer and re-gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qasentinel.chat_client import ChatClient, ChatResponse
from qasentinel.quality_gate import GateResult, Status, evaluate_answer


@dataclass
class RepairOutcome:
    attempted: bool
    improved: bool
    original_status: Status
    final_status: Status
    original_answer: str
    final_answer: str
    original_gate: GateResult
    final_gate: GateResult
    repair_response: ChatResponse | None = None
    notes: list[str] | None = None


def _status_rank(s: Status) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}[s]


def should_repair(status: Status) -> bool:
    return status in ("WARN", "FAIL")


def build_repair_prefix(question: str, answer: str, reasons: list[str]) -> str:
    reason_blob = "; ".join(reasons[:8]) if reasons else "quality issues"
    return (
        "Your previous answer failed our quality gate. Rewrite a BETTER answer only.\n"
        f"Original question: {question}\n"
        f"Gate reasons to fix: {reason_blob}\n"
        "Rules: stay on software testing; no malware/secrets; 3–6 clear sentences; "
        "use proper QA terminology. Output ONLY the improved assistant answer.\n"
        f"Previous answer:\n{answer}"
    )


def try_repair(
    question: str,
    answer: str,
    gate: GateResult,
    client: ChatClient,
    *,
    use_judge: bool = False,
    model: str | None = None,
    policy: dict[str, Any] | None = None,
    free_tier: dict[str, Any] | None = None,
) -> RepairOutcome:
    """
    If gate is WARN/FAIL and live API is available, request one rewrite and re-gate.
    Offline/golden-only: no repair attempt (returns attempted=False).
    """
    notes: list[str] = []
    if not should_repair(gate.status):
        return RepairOutcome(
            attempted=False,
            improved=False,
            original_status=gate.status,
            final_status=gate.status,
            original_answer=answer,
            final_answer=answer,
            original_gate=gate,
            final_gate=gate,
            notes=["Repair skipped — already PASS"],
        )

    if not client.has_api_key:
        return RepairOutcome(
            attempted=False,
            improved=False,
            original_status=gate.status,
            final_status=gate.status,
            original_answer=answer,
            final_answer=answer,
            original_gate=gate,
            final_gate=gate,
            notes=["Repair skipped — no API key (offline mode)"],
        )

    prefix = build_repair_prefix(question, answer, gate.reasons)
    resp = client.complete(
        question,
        model=model,
        extra_user_prefix=prefix,
    )
    if resp.error and not resp.answer:
        notes.append(f"Repair call failed: {resp.error}")
        return RepairOutcome(
            attempted=True,
            improved=False,
            original_status=gate.status,
            final_status=gate.status,
            original_answer=answer,
            final_answer=answer,
            original_gate=gate,
            final_gate=gate,
            repair_response=resp,
            notes=notes,
        )

    new_answer = (resp.answer or "").strip()
    new_gate = evaluate_answer(
        question,
        new_answer,
        use_judge=use_judge,
        judge_client=client if use_judge else None,
        policy=policy,
        free_tier=free_tier,
    )
    improved = _status_rank(new_gate.status) < _status_rank(gate.status)
    # Prefer repaired answer only if not worse
    if _status_rank(new_gate.status) <= _status_rank(gate.status) and new_answer:
        final_answer, final_gate = new_answer, new_gate
        notes.append(
            f"Repair applied: {gate.status} → {new_gate.status}"
            + (" (improved)" if improved else " (same band)")
        )
    else:
        final_answer, final_gate = answer, gate
        notes.append(
            f"Repair discarded (worse): {gate.status} vs repaired {new_gate.status}"
        )

    return RepairOutcome(
        attempted=True,
        improved=improved,
        original_status=gate.status,
        final_status=final_gate.status,
        original_answer=answer,
        final_answer=final_answer,
        original_gate=gate,
        final_gate=final_gate,
        repair_response=resp,
        notes=notes,
    )


def pick_ab_winner(
    a_answer: str,
    a_gate: GateResult,
    a_resp: ChatResponse,
    b_answer: str,
    b_gate: GateResult,
    b_resp: ChatResponse,
) -> dict[str, Any]:
    """Pick gated winner: better status, then lower latency on tie."""
    ra, rb = _status_rank(a_gate.status), _status_rank(b_gate.status)
    if ra < rb:
        winner = "A"
    elif rb < ra:
        winner = "B"
    else:
        # tie on status — prefer higher L2 must_include if applicable, else lower latency
        mi_a = (a_gate.scores.get("L2") or {}).get("must_include")
        mi_b = (b_gate.scores.get("L2") or {}).get("must_include")
        if mi_a is not None and mi_b is not None and mi_a != mi_b:
            winner = "A" if mi_a > mi_b else "B"
        else:
            winner = "A" if a_resp.latency_ms <= b_resp.latency_ms else "B"

    if winner == "A":
        return {
            "winner": "A",
            "answer": a_answer,
            "gate": a_gate,
            "response": a_resp,
            "loser_status": b_gate.status,
            "loser_model": b_resp.model,
        }
    return {
        "winner": "B",
        "answer": b_answer,
        "gate": b_gate,
        "response": b_resp,
        "loser_status": a_gate.status,
        "loser_model": a_resp.model,
    }
