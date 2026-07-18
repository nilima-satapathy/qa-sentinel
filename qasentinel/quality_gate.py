"""Layered per-answer quality gate: L1 offline · L2 golden · L3 optional judge."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from qasentinel.chat_client import ChatClient, match_golden_case
from qasentinel.paths import ROOT, ensure_import_paths

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


# Shown in chat + gate when the user question is outside software quality/testing
OUT_OF_SCOPE_REASON = (
    "The question is unrelated to software testing, which is the scope of the assistant."
)
OUT_OF_SCOPE_ANSWER = (
    "The question is unrelated to software testing, which is the scope of the assistant. "
    "Please ask about software testing, QA, test automation, CI/CD, defects, coverage, "
    "or related software quality topics."
)

# Extra question-side cues (beyond policy domain_keywords)
_DEFAULT_QUESTION_SCOPE = (
    "sdet",
    "unit test",
    "integration test",
    "e2e",
    "end to end",
    "end-to-end",
    "smoke test",
    "regression",
    "assert",
    "testcase",
    "test case",
    "test plan",
    "test suite",
    "test automation",
    "devops",
    "release",
    "defect",
    "bug",
    "quality assurance",
    "manual test",
    "functional test",
    "performance test",
    "load test",
    "security test",
    "uat",
    "staging",
    "playwright",
    "selenium",
    "cypress",
    "junit",
    "pytest",
    "postman",
    "api test",
    "ci/cd",
    "continuous integration",
    "flaky",
    "coverage",
    "verification",
    "validation",
    "shift-left",
    "shift left",
    "tdd",
    "bdd",
)


def is_attack_like_question(question: str) -> bool:
    q_lower = (question or "").lower()
    return any(
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


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Match multi-word phrases as substrings; short tokens as whole words only."""
    k = (keyword or "").strip().lower()
    if not k:
        return False
    t = (text or "").lower()
    # Multi-word or long keywords: substring is fine
    if " " in k or len(k) >= 5:
        return k in t
    # Short tokens (qa, ci, api, bug, …) — require word boundaries
    return re.search(rf"\b{re.escape(k)}\b", t) is not None


def is_software_quality_related(
    question: str,
    policy: dict[str, Any] | None = None,
) -> bool:
    """True if the user question is in scope for a software-testing / QA assistant."""
    q = (question or "").strip().lower()
    if not q:
        return False
    # Adversarial prompts stay in-scope so safety refusal can run
    if is_attack_like_question(q):
        return True
    pol = policy or {}
    keywords = [k.lower() for k in (pol.get("domain_keywords") or [])]
    keywords.extend(k.lower() for k in (pol.get("question_scope_keywords") or []))
    keywords.extend(_DEFAULT_QUESTION_SCOPE)
    return any(_keyword_in_text(k, q) for k in keywords if k)


def evaluate_l1(question: str, answer: str, policy: dict[str, Any]) -> tuple[Status, list[str], dict]:
    reasons: list[str] = []
    status: Status = "PASS"
    scores: dict[str, Any] = {}
    text = (answer or "").strip()
    min_chars = int(policy.get("min_answer_chars") or 40)
    scores["answer_chars"] = len(text)

    # Question-scope first: off-topic software-quality queries
    in_scope = is_software_quality_related(question, policy)
    scores["question_in_scope"] = in_scope
    if not in_scope:
        status = "FAIL"
        reasons.append(f"L1: {OUT_OF_SCOPE_REASON}")
        # Still run remaining checks on the answer when present

    if len(text) < min_chars:
        status = _worst(status, "FAIL")
        reasons.append(f"L1: answer too short ({len(text)} < {min_chars} chars)")

    lower = text.lower()
    for phrase in policy.get("critical_must_not") or []:
        if phrase.lower() in lower:
            status = "FAIL"
            reasons.append("L1: critical policy hit — contains disallowed content")
            break

    for phrase in policy.get("injection_fail_phrases") or []:
        if phrase.lower() in lower:
            status = "FAIL"
            reasons.append("L1: possible system-prompt / injection compliance")
            break

    # Domain fit on answer: testing keywords OR clear refusal of off-scope
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
        "unrelated to software testing",
        "qa",
    )
    has_refusal = any(c in lower for c in refusal_cues)
    scores["domain_keyword_hit"] = has_domain
    scores["refusal_cue"] = has_refusal

    attack_like = is_attack_like_question(question)
    # If question was in scope but answer is off-topic and not a refusal → WARN
    if in_scope and not has_domain and not has_refusal and not attack_like:
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


def free_tier_exhausted(free_tier: dict[str, Any] | None) -> bool:
    """True when daily free tokens or requests are used up."""
    if not free_tier:
        return False
    tok_left = int(free_tier.get("tokens_remaining") or 0)
    req_left = int(free_tier.get("requests_remaining") or 0)
    return tok_left <= 0 or req_left <= 0


def should_run_l2(
    policy: dict[str, Any],
    *,
    free_tier: dict[str, Any] | None = None,
    force_l2: bool | None = None,
) -> tuple[bool, str]:
    """
    L2 (golden) is active only when free-tier credits are exhausted.

    While free tokens/requests remain, L2 stays inactive.
    If free_tier is not provided (unit tests / batch CI), L2 runs by default
    unless policy forces the free-tier gate and no meter is present.
    """
    if force_l2 is True:
        return True, "forced on"
    if force_l2 is False:
        return False, "forced off"

    only_when_exhausted = policy.get("l2_only_when_free_tier_exhausted", True)
    if not only_when_exhausted:
        return True, "policy always-on"

    if free_tier is None:
        # No live meter (tests/batch): keep L2 available
        return True, "no free-tier meter (offline/eval default)"

    if free_tier_exhausted(free_tier):
        return True, "free-tier exhausted"
    return False, "free-tier credits remaining — L2 inactive"


def evaluate_l2(question: str, answer: str, policy: dict[str, Any]) -> tuple[Status, list[str], dict, str | None]:
    m = _p4_metrics()
    must_include_score = m.must_include_score
    must_not_include_violations = m.must_not_include_violations
    reference_overlap_score = m.reference_overlap_score

    # Broad golden match: exact → normalized → fuzzy token similarity
    min_match = float(policy.get("l2_match_min") or 0.32)
    case, match_score, match_mode = match_golden_case(question, min_score=min_match)
    if not case:
        return "PASS", [], {
            "applicable": False,
            "match_score": round(match_score, 4),
            "match_mode": None,
            "match_min": min_match,
        }, None

    mi = must_include_score(answer, case.get("must_include") or [])
    ov = reference_overlap_score(answer, case.get("reference_answer") or "")
    viol = must_not_include_violations(answer, case.get("must_not_include") or [])
    mi_pass = float(policy.get("must_include_pass") or 0.5)
    mi_warn = float(policy.get("must_include_warn") or 0.35)
    ov_pass = float(policy.get("overlap_pass") or 0.12)
    ov_warn = float(policy.get("overlap_warn") or 0.06)

    # Slightly looser bands for fuzzy (paraphrased) questions
    if match_mode == "fuzzy":
        mi_pass = max(0.25, mi_pass - 0.08)
        mi_warn = max(0.15, mi_warn - 0.08)
        ov_pass = max(0.06, ov_pass - 0.03)
        ov_warn = max(0.03, ov_warn - 0.02)

    scores = {
        "applicable": True,
        "must_include": round(mi, 4),
        "reference_overlap": round(ov, 4),
        "must_not_violations": viol,
        "case_id": case["id"],
        "match_mode": match_mode,
        "match_score": round(match_score, 4),
        "golden_question": case.get("question"),
    }
    reasons: list[str] = []
    status: Status = "PASS"

    if match_mode == "fuzzy":
        reasons.append(
            f"L2: broad match → {case['id']} "
            f"(similarity {match_score:.0%}, min {min_match:.0%})"
        )
    elif match_mode == "normalized":
        reasons.append(f"L2: normalized match → {case['id']}")

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
    *,
    reference_context: dict[str, Any] | None = None,
) -> tuple[Status, list[str], dict]:
    """
    Free-tier AI judge focused on factual accuracy of software-testing answers.
    Optionally grounded with a golden reference when a related case is found.
    """
    if client is None or not client.has_api_key:
        return "PASS", ["L3: factual judge skipped (no API key)"], {
            "applicable": False,
            "focus": "factual_accuracy",
        }

    ref_block = ""
    if reference_context:
        ref_block = (
            "\nKNOWN-GOOD REFERENCE (use to check factual accuracy; "
            "do not require word-for-word match):\n"
            f"Reference case id: {reference_context.get('id')}\n"
            f"Reference answer: {reference_context.get('reference_answer') or ''}\n"
            f"Key concepts that should appear when relevant: "
            f"{reference_context.get('must_include') or []}\n"
        )

    judge_prompt = (
        "You are a strict FACTUAL ACCURACY judge for a software-testing / QA chatbot.\n"
        "Evaluate ONLY whether the ASSISTANT answer is factually correct for the QUESTION.\n"
        "\n"
        "Scoring focus (in order):\n"
        "1) Factual accuracy of testing concepts, definitions, practices, and claims\n"
        "2) No invented standards, tools, or metrics presented as fact\n"
        "3) No critical misconceptions (e.g. wrong definition of unit/integration/E2E)\n"
        "4) If the answer refuses a harmful/off-scope request, that can be accurate\n"
        "Do NOT grade writing style or length heavily — accuracy first.\n"
        f"{ref_block}"
        "\n"
        "Return ONLY valid JSON (no markdown, no extra text):\n"
        '{"score": 0.0-1.0, "pass": true/false, '
        '"factual_accuracy": 0.0-1.0, '
        '"issues": ["short factual problems if any"], '
        '"reasons": ["1-4 short reasons"]}\n'
        "\n"
        f"QUESTION: {question}\n"
        f"ANSWER: {answer}\n"
    )
    try:
        resp = client.complete(
            "Judge FACTUAL ACCURACY of this software-testing Q&A. "
            "Return JSON only.\n" + judge_prompt
        )
        if resp.error and not resp.answer:
            return "WARN", [f"L3: factual judge call failed: {resp.error}"], {
                "applicable": True,
                "focus": "factual_accuracy",
                "error": resp.error,
            }
        raw = resp.answer.strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return "WARN", ["L3: factual judge returned non-JSON"], {
                "applicable": True,
                "focus": "factual_accuracy",
                "raw": raw[:300],
            }
        data = json.loads(m.group(0))
        score = float(data.get("score") or data.get("factual_accuracy") or 0)
        factual = float(data.get("factual_accuracy") or score)
        jpass = bool(data.get("pass")) if "pass" in data else factual >= float(
            policy.get("judge_pass") or 0.6
        )
        jreasons = [str(x) for x in (data.get("reasons") or [])][:5]
        issues = [str(x) for x in (data.get("issues") or [])][:5]
        scores = {
            "applicable": True,
            "focus": "factual_accuracy",
            "score": score,
            "factual_accuracy": factual,
            "pass": jpass,
            "reasons": jreasons,
            "issues": issues,
            "grounded_case_id": (reference_context or {}).get("id"),
            "tokens": resp.total_tokens,
            "latency_ms": resp.latency_ms,
        }
        j_pass = float(policy.get("judge_pass") or 0.6)
        j_warn = float(policy.get("judge_warn") or 0.4)
        reasons = [
            f"L3: factual accuracy score={factual:.2f}"
            + (f" (grounded {scores['grounded_case_id']})" if scores.get("grounded_case_id") else "")
        ]
        reasons.extend(f"L3: {r}" for r in jreasons)
        reasons.extend(f"L3 issue: {i}" for i in issues)
        # Prefer factual_accuracy for band decisions
        metric = factual if factual else score
        if (not jpass) or metric < j_warn:
            return "FAIL", reasons, scores
        if metric < j_pass:
            return "WARN", reasons, scores
        return "PASS", reasons, scores
    except Exception as exc:  # noqa: BLE001
        return "WARN", [f"L3: factual judge error: {exc}"], {
            "applicable": True,
            "focus": "factual_accuracy",
            "error": str(exc),
        }


def evaluate_answer(
    question: str,
    answer: str,
    *,
    use_judge: bool = False,
    judge_client: ChatClient | None = None,
    policy: dict[str, Any] | None = None,
    free_tier: dict[str, Any] | None = None,
    force_l2: bool | None = None,
) -> GateResult:
    """Run L1+L2(+L3) and aggregate status.

    L2 (golden) runs only when free-tier credits are exhausted, unless
    free_tier is omitted (tests/batch) or force_l2 is set.
    """
    pol = policy or load_policy()
    reasons: list[str] = []
    layers: dict[str, Any] = {}
    scores: dict[str, Any] = {}

    s1, r1, sc1 = evaluate_l1(question, answer, pol)
    layers["L1"] = {"status": s1, "scores": sc1}
    scores["L1"] = sc1
    reasons.extend(r1)
    status = s1

    run_l2, l2_why = should_run_l2(pol, free_tier=free_tier, force_l2=force_l2)
    gid: str | None = None
    if run_l2:
        s2, r2, sc2, gid = evaluate_l2(question, answer, pol)
        sc2 = {**sc2, "activation": l2_why}
        layers["L2"] = {"status": s2, "scores": sc2}
        scores["L2"] = sc2
        reasons.extend(r2)
        if sc2.get("applicable"):
            status = _worst(status, s2)
    else:
        s2, r2, sc2 = "PASS", [f"L2: inactive ({l2_why})"], {
            "applicable": False,
            "skipped": True,
            "activation": l2_why,
            "tokens_remaining": (free_tier or {}).get("tokens_remaining"),
            "requests_remaining": (free_tier or {}).get("requests_remaining"),
        }
        layers["L2"] = {"status": s2, "scores": sc2}
        scores["L2"] = sc2
        reasons.extend(r2)

    if use_judge:
        # While free tier has credits, ground the factual judge with a golden
        # reference when a related case exists (does not activate full L2 bands).
        ref_ctx = None
        if free_tier is not None and not free_tier_exhausted(free_tier):
            min_match = float(pol.get("l2_match_min") or 0.32)
            case, mscore, mode = match_golden_case(question, min_score=min_match)
            if case and mode:
                ref_ctx = {
                    "id": case.get("id"),
                    "reference_answer": case.get("reference_answer"),
                    "must_include": case.get("must_include"),
                    "match_mode": mode,
                    "match_score": mscore,
                }
        s3, r3, sc3 = evaluate_l3_judge(
            question,
            answer,
            pol,
            judge_client,
            reference_context=ref_ctx,
        )
        layers["L3"] = {"status": s3, "scores": sc3}
        scores["L3"] = sc3
        reasons.extend(r3)
        if sc3.get("applicable") is not False:
            status = _worst(status, s3)
    else:
        layers["L3"] = {
            "status": "PASS",
            "scores": {
                "applicable": False,
                "skipped": True,
                "focus": "factual_accuracy",
            },
        }

    if not reasons and status == "PASS":
        reasons.append("All gate layers passed")

    return GateResult(
        status=status,
        reasons=reasons,
        scores=scores,
        layers=layers,
        golden_case_id=gid,
    )
