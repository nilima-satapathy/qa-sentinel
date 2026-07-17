"""
QA Sentinel — realtime software-testing chatbot + per-answer quality gate.

  python -m streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.chat_client import ChatClient, load_red_team_prompts  # noqa: E402
from src.paths import ensure_import_paths  # noqa: E402
from src.quality_gate import evaluate_answer, load_policy  # noqa: E402
from src.store import TurnStore  # noqa: E402

st.set_page_config(
    page_title="QA Sentinel",
    page_icon="🛡️",
    layout="wide",
)

STATUS_EMOJI = {"PASS": "🟢", "WARN": "🟡", "FAIL": "🔴"}


def get_store() -> TurnStore:
    if "store" not in st.session_state:
        st.session_state.store = TurnStore()
    return st.session_state.store


def get_client() -> ChatClient:
    if "client" not in st.session_state:
        st.session_state.client = ChatClient()
    return st.session_state.client


def process_turn(question: str, use_judge: bool) -> None:
    client = get_client()
    store = get_store()
    policy = load_policy()

    with st.spinner("Getting AI answer…"):
        resp = client.complete(question)

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

    # Track usage for live calls
    if resp.backend == "openai" and not (resp.error and "fallback" in (resp.error or "")):
        store.add_usage(resp.total_tokens, requests=1)

    with st.spinner("Running quality gate…"):
        judge_client = client if use_judge else None
        gate = evaluate_answer(
            question,
            answer,
            use_judge=use_judge,
            judge_client=judge_client,
        )
        # Judge tokens
        if use_judge and gate.scores.get("L3", {}).get("tokens"):
            store.add_usage(gate.scores["L3"]["tokens"], requests=1)

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
            },
        }
    )


def main() -> None:
    st.title("🛡️ QA Sentinel")
    st.caption(
        "Realtime software-testing AI chatbot — every answer runs through a quality gate "
        "(offline rules · golden match · optional AI judge)."
    )

    # Ensure harness
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

    with st.sidebar:
        st.header("Controls")
        st.write(f"**Model:** `{client.model}`")
        st.write(f"**API key:** {'configured' if client.has_api_key else 'missing (golden offline)'}")
        use_judge = st.toggle(
            "AI-as-judge (L3)",
            value=False,
            help="Second free-tier call — showcases AI inside the quality gate",
        )

        st.subheader("Free cloud quota (today)")
        st.progress(
            min(1.0, meter["frac_tokens_left"]),
            text=f"{meter['tokens_remaining']:,} / {meter['tokens_limit']:,} tokens left",
        )
        st.caption(
            f"Requests: {meter['requests_used']:,} / {meter['requests_limit']:,}"
        )
        if meter["frac_tokens_left"] < 0.1:
            st.warning("Free budget low — turn off AI judge or use golden questions.")

        st.subheader("Session quality")
        st.metric(
            "Gated turns",
            f"{stats['pass']} PASS / {stats['total']}",
            delta=f"{stats['warn']} WARN · {stats['fail']} FAIL",
        )

        st.subheader("Red-team playground")
        attacks = load_red_team_prompts(limit=5)
        for a in attacks:
            if st.button(a["id"], key=f"rt_{a['id']}", use_container_width=True):
                process_turn(a["question"], use_judge)
                st.rerun()

        st.divider()
        if st.button("Export turns CSV"):
            path = store.export_csv()
            st.success(f"Wrote {path}")
        if st.button("Clear chat UI"):
            st.session_state.messages = []
            st.rerun()

        st.caption("Golden example: *What is a flaky test, and why is it harmful in CI?*")

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("gate"):
                g = msg["gate"]
                emoji = STATUS_EMOJI.get(g["status"], "⚪")
                meta = msg.get("meta") or {}
                st.markdown(
                    f"{emoji} **{g['status']}** · "
                    f"`{meta.get('backend')}` · {meta.get('latency_ms', 0):.0f} ms · "
                    f"tokens={meta.get('tokens')}"
                )
                with st.expander("Gate details"):
                    st.write("**Reasons**")
                    for r in g.get("reasons") or []:
                        st.write(f"- {r}")
                    st.json(g.get("scores") or {})

    prompt = st.chat_input("Ask a software testing question…")
    if prompt:
        process_turn(prompt, use_judge)
        st.rerun()


if __name__ == "__main__":
    main()
