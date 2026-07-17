"""
QA Sentinel — realtime software-testing chatbot + per-answer quality gate.

  python -m streamlit run app.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.chat_client import ChatClient, load_red_team_prompts  # noqa: E402
from src.paths import ensure_import_paths  # noqa: E402
from src.quality_gate import GateResult, evaluate_answer, load_policy  # noqa: E402
from src.repair import pick_ab_winner, try_repair  # noqa: E402
from src.store import TurnStore  # noqa: E402

st.set_page_config(
    page_title="QA Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme / CSS
# ---------------------------------------------------------------------------

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
  font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
}

/* App canvas */
.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(56, 189, 248, 0.12), transparent 55%),
    radial-gradient(900px 400px at 90% 0%, rgba(99, 102, 241, 0.14), transparent 50%),
    linear-gradient(180deg, #0b1220 0%, #0f172a 40%, #111827 100%);
  color: #e5e7eb;
}

/* Hide Streamlit chrome clutter */
#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stToolbar"] { display: none; }
.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 6rem !important;
  max-width: 1100px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.12);
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 1.5rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  color: #f8fafc !important;
  letter-spacing: -0.02em;
}

/* Hero */
.qs-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 1.35rem 1.5rem;
  margin-bottom: 1rem;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.35);
}
.qs-hero-left { flex: 1; min-width: 0; }
.qs-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7dd3fc;
  margin-bottom: 0.45rem;
}
.qs-title {
  margin: 0;
  font-size: 1.85rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #f8fafc;
  line-height: 1.15;
}
.qs-subtitle {
  margin: 0.45rem 0 0;
  color: #94a3b8;
  font-size: 0.98rem;
  line-height: 1.5;
  max-width: 52rem;
}
.qs-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.9rem;
}
.qs-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid transparent;
}
.qs-chip-soft {
  background: rgba(56, 189, 248, 0.1);
  color: #bae6fd;
  border-color: rgba(56, 189, 248, 0.22);
}
.qs-chip-ok {
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
  border-color: rgba(34, 197, 94, 0.28);
}
.qs-chip-warn {
  background: rgba(245, 158, 11, 0.12);
  color: #fcd34d;
  border-color: rgba(245, 158, 11, 0.28);
}
.qs-chip-off {
  background: rgba(148, 163, 184, 0.1);
  color: #cbd5e1;
  border-color: rgba(148, 163, 184, 0.22);
}

/* KPI strip */
.qs-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0 0 1.15rem;
}
@media (max-width: 900px) {
  .qs-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.qs-kpi {
  padding: 0.9rem 1rem;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.qs-kpi-label {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 0.35rem;
}
.qs-kpi-value {
  font-size: 1.45rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.qs-kpi-sub {
  margin-top: 0.25rem;
  font-size: 0.78rem;
  color: #64748b;
}
.qs-kpi-accent-pass .qs-kpi-value { color: #4ade80; }
.qs-kpi-accent-warn .qs-kpi-value { color: #fbbf24; }
.qs-kpi-accent-fail .qs-kpi-value { color: #f87171; }
.qs-kpi-accent-rate .qs-kpi-value { color: #38bdf8; }

/* Empty state */
.qs-empty {
  text-align: center;
  padding: 2.5rem 1.5rem;
  margin: 0.5rem 0 1rem;
  border-radius: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.45);
}
.qs-empty h3 {
  margin: 0 0 0.4rem;
  color: #f1f5f9;
  font-size: 1.2rem;
}
.qs-empty p {
  margin: 0 auto 1rem;
  max-width: 34rem;
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.55;
}
.qs-examples {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
}
.qs-example {
  padding: 0.45rem 0.8rem;
  border-radius: 10px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.2);
  color: #e0f2fe;
  font-size: 0.82rem;
}

/* Gate card under assistant messages */
.qs-gate {
  margin-top: 0.65rem;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.55);
}
.qs-gate-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  padding: 0.7rem 0.9rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}
.qs-status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.qs-status-pass {
  background: rgba(34, 197, 94, 0.18);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.35);
}
.qs-status-warn {
  background: rgba(245, 158, 11, 0.18);
  color: #fcd34d;
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.qs-status-fail {
  background: rgba(239, 68, 68, 0.18);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.35);
}
.qs-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  color: #94a3b8;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.qs-meta-dot { opacity: 0.45; }
.qs-layers {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-left: auto;
}
.qs-layer {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.18rem 0.45rem;
  border-radius: 6px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.qs-layer-pass { background: rgba(34, 197, 94, 0.15); color: #86efac; }
.qs-layer-warn { background: rgba(245, 158, 11, 0.15); color: #fcd34d; }
.qs-layer-fail { background: rgba(239, 68, 68, 0.15); color: #fca5a5; }
.qs-layer-skip { background: rgba(148, 163, 184, 0.12); color: #94a3b8; }
.qs-gate-body {
  padding: 0.75rem 0.9rem 0.85rem;
}
.qs-reason {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  padding: 0.35rem 0;
  font-size: 0.86rem;
  color: #cbd5e1;
  line-height: 1.45;
}
.qs-reason-bullet {
  flex-shrink: 0;
  width: 0.45rem;
  height: 0.45rem;
  margin-top: 0.4rem;
  border-radius: 999px;
  background: #38bdf8;
}
.qs-extra {
  margin-top: 0.55rem;
  padding-top: 0.55rem;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 0.8rem;
  color: #94a3b8;
}

/* Sidebar cards */
.qs-side-card {
  padding: 0.85rem 0.9rem;
  margin: 0.4rem 0 0.85rem;
  border-radius: 12px;
  background: rgba(30, 41, 59, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.12);
}
.qs-side-label {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 0.2rem;
}
.qs-side-value {
  font-size: 0.88rem;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  word-break: break-all;
}
.qs-section-title {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #94a3b8;
  margin: 1rem 0 0.45rem;
}

/* Chat avatars / bubbles */
div[data-testid="stChatMessage"] {
  background: rgba(15, 23, 42, 0.4) !important;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 16px !important;
  padding: 0.65rem 0.85rem !important;
  margin-bottom: 0.65rem;
}
div[data-testid="stChatMessage"] p {
  color: #e5e7eb;
}

/* Buttons */
.stButton > button {
  border-radius: 10px !important;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  background: rgba(30, 41, 59, 0.8) !important;
  color: #e2e8f0 !important;
  font-weight: 600 !important;
  transition: all 0.15s ease;
}
.stButton > button:hover {
  border-color: rgba(56, 189, 248, 0.45) !important;
  background: rgba(14, 116, 144, 0.25) !important;
  color: #f0f9ff !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #0284c7, #6366f1) !important;
  border: none !important;
  color: white !important;
}

/* Progress */
div[data-testid="stProgress"] > div {
  background: rgba(30, 41, 59, 0.9) !important;
  border-radius: 999px !important;
}
div[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #22d3ee, #818cf8) !important;
}

/* Expander */
div[data-testid="stExpander"] {
  background: rgba(15, 23, 42, 0.35);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.12);
}
</style>
"""


def inject_css() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def esc(text: Any) -> str:
    return html.escape("" if text is None else str(text))


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


def get_store() -> TurnStore:
    if "store" not in st.session_state:
        st.session_state.store = TurnStore()
    return st.session_state.store


def get_client() -> ChatClient:
    if "client" not in st.session_state:
        st.session_state.client = ChatClient()
    return st.session_state.client


def _track_usage(store: TurnStore, resp: Any, gate: GateResult, use_judge: bool) -> None:
    if resp.backend == "openai" and not (resp.error and "fallback" in (resp.error or "")):
        store.add_usage(resp.total_tokens, requests=1)
    if use_judge and gate.scores.get("L3", {}).get("tokens"):
        store.add_usage(gate.scores["L3"]["tokens"], requests=1)


def process_turn(
    question: str,
    use_judge: bool,
    *,
    enable_repair: bool = False,
    enable_ab: bool = False,
) -> None:
    client = get_client()
    store = get_store()

    with st.spinner("Getting AI answer…"):
        if enable_ab and client.has_api_key:
            model_a = client.model
            model_b = client.secondary_model()
            resp_a = client.complete(question, model=model_a)
            resp_b = client.complete(question, model=model_b)
            if (resp_a.error and not resp_a.answer) and (resp_b.error and not resp_b.answer):
                st.error(f"Model error: {resp_a.error or resp_b.error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"(error) {resp_a.error or resp_b.error}",
                        "gate": None,
                        "meta": {"backend": "openai", "model": model_a},
                    }
                )
                return
            with st.spinner("Gating A/B candidates…"):
                gate_a = evaluate_answer(
                    question,
                    resp_a.answer or "",
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                )
                gate_b = evaluate_answer(
                    question,
                    resp_b.answer or "",
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                )
            pick = pick_ab_winner(
                resp_a.answer or "",
                gate_a,
                resp_a,
                resp_b.answer or "",
                gate_b,
                resp_b,
            )
            resp = pick["response"]
            answer = pick["answer"]
            gate = pick["gate"]
            ab_meta = {
                "enabled": True,
                "winner": pick["winner"],
                "model_a": resp_a.model,
                "model_b": resp_b.model,
                "status_a": gate_a.status,
                "status_b": gate_b.status,
                "loser_status": pick["loser_status"],
            }
            for r, g in ((resp_a, gate_a), (resp_b, gate_b)):
                _track_usage(store, r, g, use_judge)
        else:
            resp = client.complete(question)
            ab_meta = {"enabled": False}
            if resp.error == "empty_question":
                st.warning("Enter a non-empty question.")
                return
            answer = resp.answer or ""
            if resp.error and not answer:
                st.error(f"Model error: {resp.error}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"(error) {resp.error}",
                        "gate": None,
                        "meta": {"backend": resp.backend, "model": resp.model},
                    }
                )
                return
            with st.spinner("Running quality gate…"):
                gate = evaluate_answer(
                    question,
                    answer,
                    use_judge=use_judge,
                    judge_client=client if use_judge else None,
                )
            _track_usage(store, resp, gate, use_judge)

    repair_meta: dict[str, Any] = {"attempted": False}
    if enable_repair and gate.status in ("WARN", "FAIL"):
        with st.spinner("Repair loop: rewriting + re-gating…"):
            outcome = try_repair(
                question,
                answer,
                gate,
                client,
                use_judge=use_judge,
                model=resp.model if resp.backend == "openai" else None,
            )
        repair_meta = {
            "attempted": outcome.attempted,
            "improved": outcome.improved,
            "original_status": outcome.original_status,
            "final_status": outcome.final_status,
            "notes": outcome.notes or [],
        }
        if outcome.attempted and outcome.repair_response:
            rr = outcome.repair_response
            if rr.backend == "openai":
                store.add_usage(rr.total_tokens, requests=1)
        answer = outcome.final_answer
        gate = outcome.final_gate
        if outcome.attempted:
            resp = outcome.repair_response or resp

    store.add_turn(
        question=question,
        answer=answer,
        gate_status=gate.status,
        scores=gate.scores,
        reasons=gate.reasons,
        latency_ms=resp.latency_ms,
        total_tokens=resp.total_tokens,
        model=resp.model,
        backend=resp.backend,
        golden_case_id=gate.golden_case_id,
    )

    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "gate": gate.to_dict(),
            "meta": {
                "backend": resp.backend,
                "model": resp.model,
                "latency_ms": resp.latency_ms,
                "tokens": resp.total_tokens,
                "error": resp.error,
                "ab": ab_meta,
                "repair": repair_meta,
            },
        }
    )


def session_pass_rate(stats: dict) -> float:
    total = stats.get("total") or 0
    if total <= 0:
        return 0.0
    return 100.0 * (stats.get("pass") or 0) / total


# ---------------------------------------------------------------------------
# UI fragments
# ---------------------------------------------------------------------------


def render_hero(client: ChatClient, pass_rate: float, stats: dict) -> None:
    mode_chip = (
        '<span class="qs-chip qs-chip-ok">Live free-tier</span>'
        if client.has_api_key
        else '<span class="qs-chip qs-chip-warn">Offline golden mode</span>'
    )
    rate_chip = (
        f'<span class="qs-chip qs-chip-soft">Session {pass_rate:.0f}% PASS</span>'
        if stats.get("total")
        else '<span class="qs-chip qs-chip-off">No gated turns yet</span>'
    )
    st.markdown(
        f"""
<div class="qs-hero">
  <div class="qs-hero-left">
    <div class="qs-kicker">🛡️ Portfolio · Project 5 · AI QA</div>
    <h1 class="qs-title">QA Sentinel</h1>
    <p class="qs-subtitle">
      Realtime software-testing assistant. Every AI answer is scored by a layered quality gate —
      offline policy, golden metrics, and optional AI-as-judge — with free-tier usage tracked live.
    </p>
    <div class="qs-badge-row">
      {mode_chip}
      {rate_chip}
      <span class="qs-chip qs-chip-soft">L1 · L2 · L3</span>
      <span class="qs-chip qs-chip-soft">Repair · A/B</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpi_strip(stats: dict, pass_rate: float, meter: dict) -> None:
    tok_left = meter.get("tokens_remaining", 0)
    tok_lim = meter.get("tokens_limit", 1) or 1
    tok_pct = 100.0 * tok_left / tok_lim
    st.markdown(
        f"""
<div class="qs-kpi-row">
  <div class="qs-kpi qs-kpi-accent-rate">
    <div class="qs-kpi-label">Pass rate</div>
    <div class="qs-kpi-value">{pass_rate:.0f}%</div>
    <div class="qs-kpi-sub">{stats.get('total', 0)} gated turns</div>
  </div>
  <div class="qs-kpi qs-kpi-accent-pass">
    <div class="qs-kpi-label">PASS</div>
    <div class="qs-kpi-value">{stats.get('pass', 0)}</div>
    <div class="qs-kpi-sub">Gate green</div>
  </div>
  <div class="qs-kpi qs-kpi-accent-warn">
    <div class="qs-kpi-label">WARN · FAIL</div>
    <div class="qs-kpi-value">{stats.get('warn', 0)} · {stats.get('fail', 0)}</div>
    <div class="qs-kpi-sub">Borderline / blocked</div>
  </div>
  <div class="qs-kpi">
    <div class="qs-kpi-label">Free tokens left</div>
    <div class="qs-kpi-value" style="font-size:1.15rem">{tok_left:,}</div>
    <div class="qs-kpi-sub">{tok_pct:.0f}% of daily budget</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        """
<div class="qs-empty">
  <h3>Start a gated conversation</h3>
  <p>
    Ask a software-testing question below, or try a golden example offline.
    Each answer gets a PASS / WARN / FAIL card with reasons.
  </p>
  <div class="qs-examples">
    <span class="qs-example">What is a flaky test, and why is it harmful in CI?</span>
    <span class="qs-example">Difference between smoke and regression testing?</span>
    <span class="qs-example">How do you design API test cases?</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _layer_class(status: str | None, skipped: bool = False) -> str:
    if skipped or not status:
        return "qs-layer-skip"
    s = (status or "").upper()
    if s == "PASS":
        return "qs-layer-pass"
    if s == "WARN":
        return "qs-layer-warn"
    if s == "FAIL":
        return "qs-layer-fail"
    return "qs-layer-skip"


def render_gate_card(gate: dict, meta: dict) -> None:
    status = (gate.get("status") or "PASS").upper()
    status_cls = {
        "PASS": "qs-status-pass",
        "WARN": "qs-status-warn",
        "FAIL": "qs-status-fail",
    }.get(status, "qs-status-warn")
    status_icon = {"PASS": "✓", "WARN": "!", "FAIL": "✕"}.get(status, "·")

    layers = gate.get("layers") or {}
    scores = gate.get("scores") or {}
    # Prefer layers if present; fall back to score applicability
    layer_bits = []
    for key in ("L1", "L2", "L3"):
        layer = layers.get(key) or {}
        sc = scores.get(key) or {}
        st_val = layer.get("status")
        skipped = bool(sc.get("skipped")) or sc.get("applicable") is False
        if key == "L2" and sc.get("applicable") is False:
            label = f"{key}: —"
            cls = "qs-layer-skip"
        elif key == "L3" and (skipped or sc.get("applicable") is False):
            label = f"{key}: off"
            cls = "qs-layer-skip"
        else:
            label = f"{key}: {st_val or '—'}"
            cls = _layer_class(st_val, skipped=False)
        layer_bits.append(f'<span class="qs-layer {cls}">{esc(label)}</span>')

    latency = meta.get("latency_ms")
    latency_s = f"{float(latency):.0f} ms" if latency is not None else "—"
    tokens = meta.get("tokens")
    tokens_s = str(tokens) if tokens is not None else "—"
    backend = meta.get("backend") or "—"
    model = meta.get("model") or "—"

    reasons_html = ""
    for r in gate.get("reasons") or []:
        reasons_html += (
            f'<div class="qs-reason"><span class="qs-reason-bullet"></span>'
            f"<span>{esc(r)}</span></div>"
        )
    if not reasons_html:
        reasons_html = (
            '<div class="qs-reason"><span class="qs-reason-bullet"></span>'
            "<span>No reasons recorded</span></div>"
        )

    extras = []
    ab = meta.get("ab") or {}
    if ab.get("enabled"):
        extras.append(
            f"A/B winner <b>{esc(ab.get('winner'))}</b> — "
            f"A {esc(ab.get('status_a'))} vs B {esc(ab.get('status_b'))}"
        )
    repair = meta.get("repair") or {}
    if repair.get("attempted"):
        extras.append(
            f"Repair {esc(repair.get('original_status'))} → "
            f"{esc(repair.get('final_status'))}"
            + (" · improved" if repair.get("improved") else "")
        )
    extras_html = ""
    if extras:
        extras_html = (
            '<div class="qs-extra">' + "<br/>".join(extras) + "</div>"
        )

    st.markdown(
        f"""
<div class="qs-gate">
  <div class="qs-gate-head">
    <span class="qs-status {status_cls}">{status_icon} {esc(status)}</span>
    <span class="qs-meta">{esc(backend)} <span class="qs-meta-dot">·</span>
      {esc(latency_s)} <span class="qs-meta-dot">·</span> {esc(tokens_s)} tok
      <span class="qs-meta-dot">·</span> {esc(model)}</span>
    <div class="qs-layers">{''.join(layer_bits)}</div>
  </div>
  <div class="qs-gate-body">
    {reasons_html}
    {extras_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar(
    client: ChatClient,
    meter: dict,
    stats: dict,
    pass_rate: float,
) -> tuple[bool, bool, bool]:
    st.markdown("### Controls")
    st.markdown('<div class="qs-section-title">Runtime</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="qs-side-card">
  <div class="qs-side-label">Model A</div>
  <div class="qs-side-value">{esc(client.model)}</div>
  <div class="qs-side-label" style="margin-top:0.55rem">Model B</div>
  <div class="qs-side-value">{esc(client.secondary_model())}</div>
  <div class="qs-side-label" style="margin-top:0.55rem">API key</div>
  <div class="qs-side-value">{'configured ✓' if client.has_api_key else 'missing · golden offline'}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="qs-section-title">Gate options</div>', unsafe_allow_html=True)
    use_judge = st.toggle(
        "AI-as-judge (L3)",
        value=False,
        help="Second free-tier call — AI inside the quality gate",
    )
    enable_repair = st.toggle(
        "Repair loop",
        value=False,
        help="On WARN/FAIL, one auto-rewrite + re-gate",
    )
    enable_ab = st.toggle(
        "A/B dual models",
        value=False,
        help="Run two free models, gate both, show the winner",
        disabled=not client.has_api_key,
    )
    if not client.has_api_key:
        st.caption("Add a free-tier key for live chat, judge, repair, and A/B.")

    st.markdown('<div class="qs-section-title">Free cloud quota</div>', unsafe_allow_html=True)
    frac = min(1.0, float(meter.get("frac_tokens_left") or 0))
    st.progress(
        frac,
        text=f"{meter['tokens_remaining']:,} / {meter['tokens_limit']:,} tokens left",
    )
    st.caption(
        f"Requests today: {meter['requests_used']:,} / {meter['requests_limit']:,}"
    )
    if meter["frac_tokens_left"] < 0.1:
        st.warning("Budget low — prefer golden questions or turn off judge / repair / A/B.")
    if meter["tokens_remaining"] <= 0:
        st.error("Daily free token budget exhausted for this app.")

    st.markdown('<div class="qs-section-title">Session</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Pass rate", f"{pass_rate:.0f}%")
    c2.metric("Turns", str(stats.get("total", 0)))
    st.caption(
        f"🟢 {stats.get('pass', 0)}  ·  🟡 {stats.get('warn', 0)}  ·  🔴 {stats.get('fail', 0)}"
    )

    st.markdown('<div class="qs-section-title">Red-team playground</div>', unsafe_allow_html=True)
    st.caption("Inject adversarial prompts to demo safety gating.")
    attacks = load_red_team_prompts(limit=5)
    for a in attacks:
        label = a["id"].replace("_", " ").replace("-", " ")
        if st.button(label, key=f"rt_{a['id']}", use_container_width=True):
            process_turn(
                a["question"],
                use_judge,
                enable_repair=enable_repair,
                enable_ab=enable_ab,
            )
            st.rerun()

    st.markdown('<div class="qs-section-title">Actions</div>', unsafe_allow_html=True)
    if st.button("⬇ Export turns CSV", use_container_width=True):
        path = get_store().export_csv()
        st.success(f"Wrote {path.name}")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Offline golden works without an API key.")
    st.caption("`python scripts/run_batch_gate.py`")

    return use_judge, enable_repair, enable_ab


def main() -> None:
    inject_css()

    try:
        ensure_import_paths()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    store = get_store()
    client = get_client()
    policy = load_policy()
    meter = store.free_tier_snapshot(policy)
    stats = store.session_stats()
    pass_rate = session_pass_rate(stats)

    with st.sidebar:
        use_judge, enable_repair, enable_ab = render_sidebar(
            client, meter, stats, pass_rate
        )

    render_hero(client, pass_rate, stats)
    render_kpi_strip(stats, pass_rate, meter)

    if not st.session_state.messages:
        render_empty_state()
        # Quick-start buttons for examples
        ex_cols = st.columns(3)
        examples = [
            "What is a flaky test, and why is it harmful in CI?",
            "What is the difference between smoke and regression testing?",
            "How should I design API test cases for a REST service?",
        ]
        for col, ex in zip(ex_cols, examples):
            short = ex if len(ex) < 42 else ex[:39] + "…"
            if col.button(short, key=f"ex_{hash(ex)}", use_container_width=True):
                process_turn(
                    ex,
                    use_judge,
                    enable_repair=enable_repair,
                    enable_ab=enable_ab,
                )
                st.rerun()

    for msg in st.session_state.messages:
        avatar = "🧑‍💻" if msg["role"] == "user" else "🛡️"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("gate"):
                render_gate_card(msg["gate"], msg.get("meta") or {})
                with st.expander("Full gate scores (JSON)"):
                    st.json(msg["gate"].get("scores") or {})
                    repair = (msg.get("meta") or {}).get("repair") or {}
                    if repair.get("notes"):
                        st.markdown("**Repair notes**")
                        for n in repair["notes"]:
                            st.write(f"- {n}")

    prompt = st.chat_input("Ask a software testing question…")
    if prompt:
        process_turn(
            prompt,
            use_judge,
            enable_repair=enable_repair,
            enable_ab=enable_ab,
        )
        st.rerun()


if __name__ == "__main__":
    main()
