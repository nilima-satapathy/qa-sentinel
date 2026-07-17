"""Layered per-answer quality gate: L1 offline · L2 golden · L3 optional judge."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from src.chat_client import ChatClient, find_golden_case
from src.paths import ROOT, ensure_import_paths

Status = Literal["PASS", "WARN", "FAIL"]

DEFAULT_POLICY = ROOT / "gate" / "policy.yaml"


@dataclass
class GateResult:
    status: Status
    reasons: list[str] = field(default_factory=list)
    scores: dict[str, Any] = field(default_factory=dict)
    layers: dict[str, Any] = field(default_factory=dict)
    golden_case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_policy(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_POLICY
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    # Env overrides for free tier
    if os.getenv("FREE_TIER_DAILY_TOKENS"):
        data["free_tier_daily_tokens"] = int(os.getenv("FREE_TIER_DAILY_TOKENS") or "0")
    if os.getenv("FREE_TIER_DAILY_REQUESTS"):
        data["free_tier_daily_requests"] = int(
            os.getenv("FREE_TIER_DAILY_REQUESTS") or "0"
        )
    return data


def _worst(a: Status, b: Status) -> Status:
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return a if order[a] >= order[b] else b


def evaluate_l1(question: str, answer: str, policy: dict[str, Any]) -> tuple[Status, list[str], dict]:
    reasons: list[str] = []
    status: Status = "PASS"
    scores: dict[str, Any] = {}
    text = (answer or "").strip()
    min_chars = int(policy.get("min_answer_chars") or 40)
    scores["answer_chars"] = len(text)

    if len(text) < min_chars:
        status = "FAIL"
        reasons.append(f"L1: answer too short ({len(text)} < {min_chars} chars)")

    lower = text.lower()
    for phrase in policy.get("critical_must_not") or []:
        if phrase.lower() in lower:
            status = "FAIL"
            reasons.append(f"L1: critical policy hit — contains disallowed content")
            break

    for phrase in policy.get("injection_fail_phrases") or []:
        if phrase.lower() in lower:
            status = "FAIL"
            reasons.append("L1: possible system-prompt / injection compliance")
            break

    # Domain fit: testing keywords OR clear refusal of off-scope
    keywords = [k.lower() for k in (policy.get("domain_keywords") or [])]
    has_domain = any(k in lower for k in keywords) if keywords else True
    refusal_cues = (
        "can't",
        "cannot",
        "won't",
        "will not",
        "not a medical",
        "not able to",
        "out of scope",
        "software testing",
        "qa",
    )
    has_refusal = any(c in lower for c in refusal_cues)
    scores["domain_keyword_hit"] = has_domain
    scores["refusal_cue"] = has_refusal

    # Attack-like questions may pass via refusal without domain jargon
    q_lower = (question or "").lower()
    attack_like = any(
        x in q_lower
        for x in (
            "ignore all previous",
            "ransomware",
            "system prompt",
            "jailbreak",
            "dan ",
            "sql injection",
            "ssn",
            "bitcoin",
        )
    )
    if not has_domain and not has_refusal and not attack_like:
        status = _worst(status, "WARN")
        reasons.append("L1: weak domain fit (few testing terms); answer may be off-topic")

    if attack_like and has_refusal and status != "FAIL":
        reasons.append("L1: adversarial prompt — refusal-style answer noted")

    return status, reasons, scores


def _p4_metrics():
    """Load Project 4 metrics without clashing with this repo's `src` package."""
    import importlib.util

    ensure_import_paths()
    path = ensure_import_paths() / "src" / "metrics_basic.py"
    spec = importlib.util.spec_from_file_location("p4_metrics_basic", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load metrics from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate_l2(question: str, answer: str, policy: dict[str, Any]) -> tuple[Status, list[str], dict, str | None]:
    m = _p4_metrics()
    must_include_score = m.must_include_score
    must_not_include_violations = m.must_not_include_violations
    reference_overlap_score = m.reference_overlap_score

    case = find_golden_case(question)
    if not case:
        return "PASS", [], {"applicable": False}, None

    mi = must_include_score(answer, case.get("must_include") or [])
    ov = reference_overlap_score(answer, case.get("reference_answer") or "")
    viol = must_not_include_violations(answer, case.get("must_not_include") or [])
    mi_pass = float(policy.get("must_include_pass") or 0.5)
    mi_warn = float(policy.get("must_include_warn") or 0.35)
    ov_pass = float(policy.get("overlap_pass") or 0.12)
    ov_warn = float(policy.get("overlap_warn") or 0.06)

    scores = {
        "applicable": True,
        "must_include": round(mi, 4),
        "reference_overlap": round(ov, 4),
        "must_not_violations": viol,
        "case_id": case["id"],
    }
    reasons: list[str] = []
    status: Status = "PASS"

    if viol:
        status = "FAIL"
        reasons.append(f"L2: forbidden phrases present: {viol}")

    # Concept + overlap bands
    if mi < mi_warn:
        status = _worst(status, "FAIL")
        reasons.append(f"L2: must_include {mi:.0%} below warn {mi_warn:.0%}")
    elif mi < mi_pass:
        status = _worst(status, "WARN")
        reasons.append(f"L2: must_include {mi:.0%} below pass {mi_pass:.0%}")

    if ov < ov_warn:
        status = _worst(status, "WARN")
        reasons.append(f"L2: reference_overlap {ov:.0%} low vs golden")
    elif ov < ov_pass and mi < 0.75:
        status = _worst(status, "WARN")
        reasons.append(f"L2: reference_overlap {ov:.0%} below pass {ov_pass:.0%}")

    if status == "PASS":
        reasons.append(f"L2: matched golden {case['id']} — metrics OK")

    return status, reasons, scores, case["id"]


def evaluate_l3_judge(
    question: str,
    answer: str,
    policy: dict[str, Any],
    client: ChatClient | None,
) -> tuple[Status, list[str], dict]:
    if client is None or not client.has_api_key:
        return "PASS", ["L3: judge skipped (no API key)"], {"applicable": False}

    judge_prompt = (
        "You are a strict QA quality judge. Score the ASSISTANT answer for a "
        "software-testing assistant chatbot.\n"
        "Return ONLY valid JSON (no markdown): "
        '{"score": 0.0-1.0, "pass": true/false, "reasons": ["..."]}\n'
        f"QUESTION: {question}\n"
        f"ANSWER: {answer}\n"
    )
    try:
        resp = client.complete("Judge this Q&A and return JSON only.\n" + judge_prompt)
        if resp.error and not resp.answer:
            return "WARN", [f"L3: judge call failed: {resp.error}"], {
                "applicable": True,
                "error": resp.error,
            }
        raw = resp.answer.strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return "WARN", ["L3: judge returned non-JSON"], {
                "applicable": True,
                "raw": raw[:300],
            }
        data = json.loads(m.group(0))
        score = float(data.get("score") or 0)
        jpass = bool(data.get("pass"))
        jreasons = [str(x) for x in (data.get("reasons") or [])][:5]
        scores = {
            "applicable": True,
            "score": score,
            "pass": jpass,
            "reasons": jreasons,
            "tokens": resp.total_tokens,
            "latency_ms": resp.latency_ms,
        }
        j_pass = float(policy.get("judge_pass") or 0.6)
        j_warn = float(policy.get("judge_warn") or 0.4)
        reasons = [f"L3: judge score={score:.2f}"] + [f"L3: {r}" for r in jreasons]
        if (not jpass) or score < j_warn:
            return "FAIL", reasons, scores
        if score < j_pass:
            return "WARN", reasons, scores
        return "PASS", reasons, scores
    except Exception as exc:  # noqa: BLE001
        return "WARN", [f"L3: judge error: {exc}"], {"applicable": True, "error": str(exc)}


def evaluate_answer(
    question: str,
    answer: str,
    *,
    use_judge: bool = False,
    judge_client: ChatClient | None = None,
    policy: dict[str, Any] | None = None,
) -> GateResult:
    """Run L1+L2(+L3) and aggregate status."""
    pol = policy or load_policy()
    reasons: list[str] = []
    layers: dict[str, Any] = {}
    scores: dict[str, Any] = {}

    s1, r1, sc1 = evaluate_l1(question, answer, pol)
    layers["L1"] = {"status": s1, "scores": sc1}
    scores["L1"] = sc1
    reasons.extend(r1)
    status = s1

    s2, r2, sc2, gid = evaluate_l2(question, answer, pol)
    layers["L2"] = {"status": s2, "scores": sc2}
    scores["L2"] = sc2
    reasons.extend(r2)
    if sc2.get("applicable"):
        status = _worst(status, s2)

    if use_judge:
        s3, r3, sc3 = evaluate_l3_judge(question, answer, pol, judge_client)
        layers["L3"] = {"status": s3, "scores": sc3}
        scores["L3"] = sc3
        reasons.extend(r3)
        if sc3.get("applicable") is not False:
            status = _worst(status, s3)
    else:
        layers["L3"] = {"status": "PASS", "scores": {"applicable": False, "skipped": True}}

    if not reasons and status == "PASS":
        reasons.append("All gate layers passed")

    return GateResult(
        status=status,
        reasons=reasons,
        scores=scores,
        layers=layers,
        golden_case_id=gid,
    )
