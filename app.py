"""
QA Sentinel — Design 1: Chat + Quality Artifact panel (dark / soft light themes).

  python -m streamlit run app.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any, Literal

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

ThemeName = Literal["dark", "light"]

st.set_page_config(
    page_title="QA Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Themes — Design 1 Chat + Artifact
# ---------------------------------------------------------------------------

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.stApp {
  background: var(--qs-bg);
  color: var(--qs-text);
}

#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stToolbar"] { display: none; }

.block-container {
  padding-top: 0.85rem !important;
  padding-bottom: 5.5rem !important;
  padding-left: 1.25rem !important;
  padding-right: 1.25rem !important;
  max-width: 1400px;
}

/* Top bar */
.qs-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
  padding: 0.35rem 0.15rem 0.85rem;
  border-bottom: 1px solid var(--qs-border);
}
.qs-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.qs-logo {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: linear-gradient(135deg, #10b981, #34d399);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  box-shadow: 0 0 20px var(--qs-logo-glow);
}
.qs-brand-name {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--qs-text-strong);
}
.qs-brand-sub {
  font-size: 0.72rem;
  color: var(--qs-muted);
  font-weight: 500;
}
.qs-top-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}
.qs-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  border: 1px solid var(--qs-border);
  background: var(--qs-pill-bg);
  color: var(--qs-muted-strong);
}
.qs-pill-live {
  color: var(--qs-pass);
  border-color: var(--qs-pass-border);
  background: var(--qs-pass-bg);
}
.qs-pill-off {
  color: var(--qs-warn);
  border-color: var(--qs-warn-border);
  background: var(--qs-warn-bg);
}

.qs-session-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--qs-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}

.qs-chat-shell {
  min-height: 420px;
  border-radius: 16px;
  background: var(--qs-surface);
  border: 1px solid var(--qs-border);
  padding: 1rem 1.1rem 0.85rem;
  box-shadow: var(--qs-shadow-soft);
}

.qs-empty {
  text-align: center;
  padding: 2.75rem 1.25rem 2rem;
}
.qs-empty-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 0.85rem;
  border-radius: 14px;
  background: var(--qs-pass-bg);
  border: 1px solid var(--qs-pass-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
}
.qs-empty h3 {
  margin: 0 0 0.4rem;
  color: var(--qs-text-strong);
  font-size: 1.15rem;
  font-weight: 600;
}
.qs-empty p {
  margin: 0 auto;
  max-width: 28rem;
  color: var(--qs-muted-strong);
  font-size: 0.9rem;
  line-height: 1.55;
}

div[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 0.35rem 0 !important;
  margin-bottom: 0.35rem;
}
div[data-testid="stChatMessage"] p {
  color: var(--qs-text);
  line-height: 1.55;
}

.qs-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.45rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.qs-status-pass {
  background: var(--qs-pass-bg);
  color: var(--qs-pass);
  border: 1px solid var(--qs-pass-border);
}
.qs-status-warn {
  background: var(--qs-warn-bg);
  color: var(--qs-warn);
  border: 1px solid var(--qs-warn-border);
}
.qs-status-fail {
  background: var(--qs-fail-bg);
  color: var(--qs-fail);
  border: 1px solid var(--qs-fail-border);
}
.qs-status-meta {
  font-weight: 500;
  opacity: 0.85;
}

.qs-freebar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.85rem;
  padding: 0.55rem 0.7rem;
  border-radius: 10px;
  background: var(--qs-inset);
  border: 1px solid var(--qs-border);
}
.qs-freebar-label {
  font-size: 0.72rem;
  color: var(--qs-muted-strong);
  white-space: nowrap;
  font-weight: 500;
}
.qs-freebar-track {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: var(--qs-track);
  overflow: hidden;
}
.qs-freebar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #10b981, #34d399);
}
.qs-freebar-nums {
  font-size: 0.72rem;
  color: var(--qs-muted);
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  white-space: nowrap;
}

.qs-artifact {
  border-radius: 16px;
  background: var(--qs-surface);
  border: 1px solid var(--qs-artifact-border);
  box-shadow: var(--qs-artifact-shadow);
  overflow: hidden;
  position: sticky;
  top: 0.5rem;
}
.qs-artifact-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--qs-border);
  background: var(--qs-artifact-head);
}
.qs-artifact-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--qs-text-strong);
  letter-spacing: -0.01em;
}
.qs-artifact-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.qs-badge-pass {
  background: var(--qs-pass-bg);
  color: var(--qs-pass);
}
.qs-badge-warn {
  background: var(--qs-warn-bg);
  color: var(--qs-warn);
}
.qs-badge-fail {
  background: var(--qs-fail-bg);
  color: var(--qs-fail);
}
.qs-badge-idle {
  background: var(--qs-pill-bg);
  color: var(--qs-muted);
}
.qs-artifact-body {
  padding: 1.1rem 1rem 1.15rem;
}
.qs-ring-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 1.1rem;
}
.qs-ring {
  width: 118px;
  height: 118px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 5px solid var(--qs-ring-idle);
  background: var(--qs-ring-bg);
}
.qs-ring-pass {
  border-color: #10b981;
  box-shadow: 0 0 28px var(--qs-ring-glow-pass);
}
.qs-ring-warn {
  border-color: #f59e0b;
  box-shadow: 0 0 28px var(--qs-ring-glow-warn);
}
.qs-ring-fail {
  border-color: #ef4444;
  box-shadow: 0 0 28px var(--qs-ring-glow-fail);
}
.qs-ring-idle { border-color: var(--qs-ring-idle); }
.qs-ring-status {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--qs-text-strong);
}
.qs-ring-sub {
  font-size: 0.7rem;
  color: var(--qs-muted);
  margin-top: 0.15rem;
}
.qs-layer-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}
.qs-layer-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border-radius: 10px;
  background: var(--qs-inset);
  border: 1px solid var(--qs-border);
  font-size: 0.78rem;
}
.qs-layer-name {
  font-weight: 600;
  color: var(--qs-muted-strong);
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 0.72rem;
}
.qs-layer-val { font-weight: 600; font-size: 0.72rem; }
.qs-ok { color: var(--qs-pass); }
.qs-wn { color: var(--qs-warn); }
.qs-fl { color: var(--qs-fail); }
.qs-sk { color: var(--qs-muted); }
.qs-section {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--qs-muted);
  margin: 0.35rem 0 0.45rem;
}
.qs-reason {
  display: flex;
  gap: 0.45rem;
  align-items: flex-start;
  padding: 0.28rem 0;
  font-size: 0.8rem;
  color: var(--qs-text);
  line-height: 1.4;
}
.qs-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  margin-top: 0.4rem;
  flex-shrink: 0;
}
.qs-idle-hint {
  text-align: center;
  padding: 0.5rem 0.25rem 0.25rem;
  color: var(--qs-muted);
  font-size: 0.82rem;
  line-height: 1.5;
}
.qs-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.45rem;
  margin-top: 0.85rem;
}
.qs-meta-card {
  padding: 0.5rem 0.55rem;
  border-radius: 10px;
  background: var(--qs-inset);
  border: 1px solid var(--qs-border);
}
.qs-meta-card .k {
  font-size: 0.65rem;
  color: var(--qs-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.qs-meta-card .v {
  font-size: 0.82rem;
  color: var(--qs-text-strong);
  font-weight: 600;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  margin-top: 0.15rem;
}

.qs-chips-label {
  font-size: 0.7rem;
  color: var(--qs-muted);
  font-weight: 600;
  margin: 0.35rem 0 0.25rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

section[data-testid="stSidebar"] {
  background: var(--qs-sidebar) !important;
  border-right: 1px solid var(--qs-border);
}
section[data-testid="stSidebar"] .block-container {
  padding-top: 1.25rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
  color: var(--qs-text) !important;
}

.stButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--qs-border) !important;
  background: var(--qs-btn-bg) !important;
  color: var(--qs-text-strong) !important;
  font-weight: 600 !important;
}
.stButton > button:hover {
  border-color: var(--qs-pass-border) !important;
  background: var(--qs-pass-bg) !important;
  color: var(--qs-text-strong) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #059669, #10b981) !important;
  border: none !important;
  color: white !important;
}

div[data-testid="stProgress"] > div {
  background: var(--qs-track) !important;
  border-radius: 999px !important;
}
div[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #10b981, #34d399) !important;
}
div[data-testid="stExpander"] {
  background: var(--qs-inset);
  border-radius: 10px;
  border: 1px solid var(--qs-border);
}

/* Chat input */
div[data-testid="stChatInput"] textarea {
  color: var(--qs-text) !important;
}
</style>
"""

DARK_VARS = """
<style>
.stApp {
  --qs-bg: #12141a;
  --qs-surface: #1a1d24;
  --qs-sidebar: #16181f;
  --qs-inset: rgba(0,0,0,0.25);
  --qs-border: rgba(255,255,255,0.06);
  --qs-text: #e8eaed;
  --qs-text-strong: #f8fafc;
  --qs-muted: #6b7280;
  --qs-muted-strong: #9ca3af;
  --qs-pill-bg: rgba(255,255,255,0.04);
  --qs-pass: #6ee7b7;
  --qs-pass-bg: rgba(16, 185, 129, 0.12);
  --qs-pass-border: rgba(52, 211, 153, 0.35);
  --qs-warn: #fcd34d;
  --qs-warn-bg: rgba(245, 158, 11, 0.12);
  --qs-warn-border: rgba(251, 191, 36, 0.35);
  --qs-fail: #fca5a5;
  --qs-fail-bg: rgba(239, 68, 68, 0.12);
  --qs-fail-border: rgba(248, 113, 113, 0.35);
  --qs-track: rgba(255,255,255,0.08);
  --qs-logo-glow: rgba(52, 211, 153, 0.25);
  --qs-artifact-border: rgba(52, 211, 153, 0.18);
  --qs-artifact-shadow: 0 0 40px rgba(16, 185, 129, 0.06);
  --qs-artifact-head: rgba(16, 185, 129, 0.06);
  --qs-ring-idle: #374151;
  --qs-ring-bg: radial-gradient(circle at 40% 35%, rgba(255,255,255,0.04), transparent 55%);
  --qs-ring-glow-pass: rgba(16, 185, 129, 0.25);
  --qs-ring-glow-warn: rgba(245, 158, 11, 0.2);
  --qs-ring-glow-fail: rgba(239, 68, 68, 0.2);
  --qs-btn-bg: rgba(255,255,255,0.04);
  --qs-shadow-soft: none;
  color: #e8eaed;
  background: #12141a;
}
</style>
"""

LIGHT_VARS = """
<style>
.stApp {
  --qs-bg: #f7f6f3;
  --qs-surface: #ffffff;
  --qs-sidebar: #f0eeea;
  --qs-inset: #f3f2ef;
  --qs-border: rgba(15, 23, 42, 0.08);
  --qs-text: #1f2937;
  --qs-text-strong: #0f172a;
  --qs-muted: #94a3b8;
  --qs-muted-strong: #64748b;
  --qs-pill-bg: rgba(15, 23, 42, 0.04);
  --qs-pass: #059669;
  --qs-pass-bg: rgba(16, 185, 129, 0.12);
  --qs-pass-border: rgba(16, 185, 129, 0.35);
  --qs-warn: #b45309;
  --qs-warn-bg: rgba(245, 158, 11, 0.14);
  --qs-warn-border: rgba(245, 158, 11, 0.35);
  --qs-fail: #dc2626;
  --qs-fail-bg: rgba(239, 68, 68, 0.1);
  --qs-fail-border: rgba(239, 68, 68, 0.3);
  --qs-track: rgba(15, 23, 42, 0.08);
  --qs-logo-glow: rgba(16, 185, 129, 0.2);
  --qs-artifact-border: rgba(16, 185, 129, 0.22);
  --qs-artifact-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
  --qs-artifact-head: rgba(16, 185, 129, 0.08);
  --qs-ring-idle: #d1d5db;
  --qs-ring-bg: radial-gradient(circle at 40% 35%, rgba(16, 185, 129, 0.06), transparent 55%);
  --qs-ring-glow-pass: rgba(16, 185, 129, 0.18);
  --qs-ring-glow-warn: rgba(245, 158, 11, 0.15);
  --qs-ring-glow-fail: rgba(239, 68, 68, 0.12);
  --qs-btn-bg: #ffffff;
  --qs-shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.04);
  color: #1f2937;
  background:
    radial-gradient(900px 400px at 10% -5%, rgba(16, 185, 129, 0.07), transparent 50%),
    radial-gradient(700px 320px at 90% 0%, rgba(99, 102, 241, 0.05), transparent 45%),
    #f7f6f3;
}
/* Streamlit light chrome tweaks */
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label {
  color: #1f2937 !important;
}
div[data-testid="stChatInput"] {
  background: transparent;
}
</style>
"""


def get_theme() -> ThemeName:
    t = st.session_state.get("theme", "dark")
    return "light" if t == "light" else "dark"


def set_theme(theme: ThemeName) -> None:
    st.session_state.theme = theme
    # Keep radio widget in sync when toggled from the main-canvas button
    st.session_state.theme_radio = (
        "☀️ Soft light" if theme == "light" else "🌙 Dark"
    )


def inject_css(theme: ThemeName) -> None:
    vars_css = LIGHT_VARS if theme == "light" else DARK_VARS
    st.markdown(vars_css + BASE_CSS, unsafe_allow_html=True)


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
                st.session_state.last_gate = None
                st.session_state.last_meta = {}
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
                st.session_state.last_gate = None
                st.session_state.last_meta = {}
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

    meta = {
        "backend": resp.backend,
        "model": resp.model,
        "latency_ms": resp.latency_ms,
        "tokens": resp.total_tokens,
        "error": resp.error,
        "ab": ab_meta,
        "repair": repair_meta,
    }
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "gate": gate.to_dict(),
            "meta": meta,
        }
    )
    st.session_state.last_gate = gate.to_dict()
    st.session_state.last_meta = meta


def session_pass_rate(stats: dict) -> float:
    total = stats.get("total") or 0
    if total <= 0:
        return 0.0
    return 100.0 * (stats.get("pass") or 0) / total


# ---------------------------------------------------------------------------
# UI pieces
# ---------------------------------------------------------------------------


def _layer_status(gate: dict, key: str) -> tuple[str, str]:
    layers = gate.get("layers") or {}
    scores = gate.get("scores") or {}
    layer = layers.get(key) or {}
    sc = scores.get(key) or {}
    st_val = (layer.get("status") or "").upper()

    if key == "L3" and (sc.get("skipped") or sc.get("applicable") is False):
        return "off", "qs-sk"
    if key == "L2" and sc.get("applicable") is False:
        return "n/a", "qs-sk"
    if st_val == "PASS":
        return "PASS", "qs-ok"
    if st_val == "WARN":
        return "WARN", "qs-wn"
    if st_val == "FAIL":
        return "FAIL", "qs-fl"
    return "—", "qs-sk"


def render_status_chip(gate: dict, meta: dict) -> None:
    status = (gate.get("status") or "PASS").upper()
    cls = {
        "PASS": "qs-status-pass",
        "WARN": "qs-status-warn",
        "FAIL": "qs-status-fail",
    }.get(status, "qs-status-warn")
    icon = {"PASS": "✓", "WARN": "!", "FAIL": "✕"}.get(status, "·")
    latency = meta.get("latency_ms")
    lat = f"{float(latency):.0f} ms" if latency is not None else "—"
    backend = meta.get("backend") or "—"
    st.markdown(
        f'<div class="qs-status-chip {cls}">'
        f"{icon} {esc(status)}"
        f'<span class="qs-status-meta">· Quality Gate · {esc(lat)} · {esc(backend)}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_artifact_panel(gate: dict | None, meta: dict | None) -> None:
    if not gate:
        st.markdown(
            """
<div class="qs-artifact">
  <div class="qs-artifact-head">
    <span class="qs-artifact-title">Quality Gate</span>
    <span class="qs-artifact-badge qs-badge-idle">Idle</span>
  </div>
  <div class="qs-artifact-body">
    <div class="qs-ring-wrap">
      <div class="qs-ring qs-ring-idle">
        <div class="qs-ring-status" style="font-size:0.95rem;opacity:0.55">—</div>
        <div class="qs-ring-sub">awaiting turn</div>
      </div>
    </div>
    <div class="qs-idle-hint">
      Ask a testing question.<br/>
      Every answer is scored here as an <b>artifact</b> — L1 · L2 · L3.
    </div>
    <div class="qs-section">Layers</div>
    <div class="qs-layer-list">
      <div class="qs-layer-row"><span class="qs-layer-name">L1 Offline</span><span class="qs-layer-val qs-sk">—</span></div>
      <div class="qs-layer-row"><span class="qs-layer-name">L2 Golden</span><span class="qs-layer-val qs-sk">—</span></div>
      <div class="qs-layer-row"><span class="qs-layer-name">L3 AI Judge</span><span class="qs-layer-val qs-sk">off</span></div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    status = (gate.get("status") or "PASS").upper()
    ring_cls = {
        "PASS": "qs-ring-pass",
        "WARN": "qs-ring-warn",
        "FAIL": "qs-ring-fail",
    }.get(status, "qs-ring-idle")
    badge_cls = {
        "PASS": "qs-badge-pass",
        "WARN": "qs-badge-warn",
        "FAIL": "qs-badge-fail",
    }.get(status, "qs-badge-idle")

    layers_html = ""
    layer_labels = {
        "L1": "L1 Offline policy",
        "L2": "L2 Golden match",
        "L3": "L3 AI judge",
    }
    for key in ("L1", "L2", "L3"):
        val, cls = _layer_status(gate, key)
        layers_html += (
            f'<div class="qs-layer-row">'
            f'<span class="qs-layer-name">{esc(layer_labels[key])}</span>'
            f'<span class="qs-layer-val {cls}">{esc(val)}</span>'
            f"</div>"
        )

    reasons_html = ""
    for r in (gate.get("reasons") or [])[:6]:
        reasons_html += (
            f'<div class="qs-reason"><span class="qs-dot"></span>'
            f"<span>{esc(r)}</span></div>"
        )
    if not reasons_html:
        reasons_html = (
            '<div class="qs-reason"><span class="qs-dot"></span>'
            "<span>No reasons recorded</span></div>"
        )

    meta = meta or {}
    latency = meta.get("latency_ms")
    lat_s = f"{float(latency):.0f} ms" if latency is not None else "—"
    tokens = meta.get("tokens")
    tok_s = str(tokens) if tokens is not None else "—"
    model = meta.get("model") or "—"
    backend = meta.get("backend") or "—"

    extras = []
    ab = meta.get("ab") or {}
    if ab.get("enabled"):
        extras.append(
            f"A/B winner {esc(ab.get('winner'))}: "
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
            '<div class="qs-section">Extras</div>'
            + "".join(
                f'<div class="qs-reason"><span class="qs-dot"></span><span>{x}</span></div>'
                for x in extras
            )
        )

    st.markdown(
        f"""
<div class="qs-artifact">
  <div class="qs-artifact-head">
    <span class="qs-artifact-title">Quality Gate</span>
    <span class="qs-artifact-badge {badge_cls}">{esc(status)}</span>
  </div>
  <div class="qs-artifact-body">
    <div class="qs-ring-wrap">
      <div class="qs-ring {ring_cls}">
        <div class="qs-ring-status">{esc(status)}</div>
        <div class="qs-ring-sub">{esc(backend)}</div>
      </div>
    </div>
    <div class="qs-section">Layers</div>
    <div class="qs-layer-list">{layers_html}</div>
    <div class="qs-section">Key reasons</div>
    {reasons_html}
    {extras_html}
    <div class="qs-meta-grid">
      <div class="qs-meta-card"><div class="k">Latency</div><div class="v">{esc(lat_s)}</div></div>
      <div class="qs-meta-card"><div class="k">Tokens</div><div class="v">{esc(tok_s)}</div></div>
      <div class="qs-meta-card" style="grid-column:1/-1"><div class="k">Model</div><div class="v">{esc(model)}</div></div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_topbar(client: ChatClient, meter: dict, pass_rate: float, stats: dict) -> None:
    mode = (
        '<span class="qs-pill qs-pill-live">● Live free-tier</span>'
        if client.has_api_key
        else '<span class="qs-pill qs-pill-off">● Offline golden</span>'
    )
    rate = (
        f'<span class="qs-pill">Session {pass_rate:.0f}% PASS</span>'
        if stats.get("total")
        else '<span class="qs-pill">No gated turns yet</span>'
    )
    tokens = f'<span class="qs-pill">{meter["tokens_remaining"]:,} tokens left</span>'
    theme = get_theme()
    theme_label = "Soft light" if theme == "light" else "Dark"
    st.markdown(
        f"""
<div class="qs-topbar">
  <div class="qs-brand">
    <div class="qs-logo">🛡️</div>
    <div>
      <div class="qs-brand-name">QA Sentinel</div>
      <div class="qs-brand-sub">Chat + quality gate artifact · {esc(theme_label)}</div>
    </div>
  </div>
  <div class="qs-top-meta">
    {mode}
    {rate}
    {tokens}
    <span class="qs-pill">{esc(client.model)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_freebar(meter: dict) -> None:
    used = meter["tokens_used"]
    limit = meter["tokens_limit"] or 1
    frac = min(1.0, used / limit) if limit else 0
    pct = int(round(frac * 100))
    st.markdown(
        f"""
<div class="qs-freebar">
  <span class="qs-freebar-label">Free tier</span>
  <div class="qs-freebar-track"><div class="qs-freebar-fill" style="width:{pct}%"></div></div>
  <span class="qs-freebar-nums">{used:,} / {limit:,} · {meter['tokens_remaining']:,} left</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_theme_toggle() -> ThemeName:
    """Segmented theme control; returns current theme after update."""
    current = get_theme()
    options = ["🌙 Dark", "☀️ Soft light"]
    if "theme_radio" not in st.session_state:
        st.session_state.theme_radio = (
            "☀️ Soft light" if current == "light" else "🌙 Dark"
        )
    choice = st.radio(
        "Theme",
        options,
        horizontal=True,
        label_visibility="collapsed",
        key="theme_radio",
    )
    new_theme: ThemeName = "light" if "light" in choice.lower() else "dark"
    if new_theme != current:
        st.session_state.theme = new_theme
        st.rerun()
    return new_theme


EXAMPLE_PROMPTS = [
    "What is a flaky test, and why is it harmful in CI?",
    "What is the difference between smoke and regression testing?",
    "How should I design API test cases for a REST service?",
    "What is shift-left testing?",
]


def main() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"

    theme = get_theme()
    inject_css(theme)

    try:
        ensure_import_paths()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_gate" not in st.session_state:
        st.session_state.last_gate = None
    if "last_meta" not in st.session_state:
        st.session_state.last_meta = {}

    store = get_store()
    client = get_client()
    policy = load_policy()
    meter = store.free_tier_snapshot(policy)
    stats = store.session_stats()
    pass_rate = session_pass_rate(stats)

    with st.sidebar:
        st.markdown("### Appearance")
        render_theme_toggle()
        st.caption("Dark · Soft light (Design 1)")
        st.divider()
        st.markdown("### Settings")
        st.caption("Gate options & red-team")
        use_judge = st.toggle(
            "AI-as-judge (L3)",
            value=False,
            help="Second free-tier call — AI inside the quality gate",
        )
        enable_repair = st.toggle("Repair loop", value=False)
        enable_ab = st.toggle(
            "A/B dual models",
            value=False,
            disabled=not client.has_api_key,
        )
        st.divider()
        st.markdown("**Red-team playground**")
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
        st.divider()
        if st.button("Export turns CSV", use_container_width=True):
            path = store.export_csv()
            st.success(f"Wrote {path.name}")
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_gate = None
            st.session_state.last_meta = {}
            st.rerun()
        st.caption(f"Model B: `{client.secondary_model()}`")

    # Compact theme switch on main canvas (next to top bar)
    t1, t2 = st.columns([5, 1.2])
    with t1:
        render_topbar(client, meter, pass_rate, stats)
    with t2:
        st.markdown('<div style="height:0.35rem"></div>', unsafe_allow_html=True)
        current = get_theme()
        if current == "dark":
            if st.button("☀️ Light", key="theme_main_to_light", use_container_width=True):
                set_theme("light")
                st.rerun()
        else:
            if st.button("🌙 Dark", key="theme_main_to_dark", use_container_width=True):
                set_theme("dark")
                st.rerun()

    chat_col, art_col = st.columns([1.55, 1], gap="medium")

    with chat_col:
        st.markdown(
            '<div class="qs-session-label">Conversation</div>',
            unsafe_allow_html=True,
        )

        if not st.session_state.messages:
            st.markdown(
                """
<div class="qs-chat-shell">
  <div class="qs-empty">
    <div class="qs-empty-icon">🛡️</div>
    <h3>Start a gated conversation</h3>
    <p>
      Ask a software-testing question. The answer appears here;
      the <b>Quality Gate</b> artifact on the right scores every turn.
    </p>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.messages:
                avatar = "🧑‍💻" if msg["role"] == "user" else "🛡️"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and msg.get("gate"):
                        render_status_chip(msg["gate"], msg.get("meta") or {})

        render_freebar(meter)

        st.markdown(
            '<div class="qs-chips-label">Try</div>',
            unsafe_allow_html=True,
        )
        chip_cols = st.columns(4)
        for i, ex in enumerate(EXAMPLE_PROMPTS):
            short = ex if len(ex) < 28 else ex[:25] + "…"
            if chip_cols[i].button(short, key=f"chip_{i}", use_container_width=True):
                process_turn(
                    ex,
                    use_judge,
                    enable_repair=enable_repair,
                    enable_ab=enable_ab,
                )
                st.rerun()

    with art_col:
        render_artifact_panel(
            st.session_state.last_gate,
            st.session_state.last_meta,
        )
        if st.session_state.last_gate:
            with st.expander("Full scores (JSON)"):
                st.json(st.session_state.last_gate.get("scores") or {})

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
