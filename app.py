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
from src.quality_gate import GateResult, evaluate_answer  # noqa: E402
from src.repair import pick_ab_winner, try_repair  # noqa: E402
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


def _track_usage(store: TurnStore, resp, gate: GateResult, use_judge: bool) -> None:
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
            # Gate both candidates offline (+ optional judge)
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
            # Usage for both candidates
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

    repair_meta = {"attempted": False}
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
            if use_judge and outcome.final_gate.scores.get("L3", {}).get("tokens"):
                # judge may have run again on repair
                pass
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


def main() -> None:
    st.title("🛡️ QA Sentinel")
    st.caption(
        "Realtime software-testing AI chatbot — every answer runs through a quality gate "
        "(offline rules · golden match · optional AI judge · repair / A/B stretch)."
    )

    try:
        ensure_import_paths()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    store = get_store()
    client = get_client()
    from src.quality_gate import load_policy

    policy = load_policy()
    meter = store.free_tier_snapshot(policy)
    stats = store.session_stats()
    pass_rate = session_pass_rate(stats)

    # Session quality banner (stretch 10.3)
    if stats["total"] > 0:
        if pass_rate >= 70:
            banner_kind = "success"
        elif pass_rate >= 40:
            banner_kind = "warning"
        else:
            banner_kind = "error"
        getattr(st, banner_kind)(
            f"**Session quality score:** {pass_rate:.0f}% PASS "
            f"({stats['pass']} pass · {stats['warn']} warn · {stats['fail']} fail "
            f"of {stats['total']} gated turns)"
        )
    else:
        st.info(
            "Session quality score appears after your first gated turn. "
            "Try: *What is a flaky test, and why is it harmful in CI?*"
        )

    with st.sidebar:
        st.header("Controls")
        st.write(f"**Model A:** `{client.model}`")
        st.write(f"**Model B:** `{client.secondary_model()}`")
        st.write(
            f"**API key:** {'configured' if client.has_api_key else 'missing (golden offline)'}"
        )
        use_judge = st.toggle(
            "AI-as-judge (L3)",
            value=False,
            help="Second free-tier call — showcases AI inside the quality gate",
        )
        enable_repair = st.toggle(
            "Repair loop (stretch)",
            value=False,
            help="On WARN/FAIL, one auto-rewrite + re-gate (uses free-tier credits)",
        )
        enable_ab = st.toggle(
            "A/B dual models (stretch)",
            value=False,
            help="Run two free models, gate both, show the winner",
            disabled=not client.has_api_key,
        )
        if enable_ab and not client.has_api_key:
            st.caption("A/B needs a free-tier API key.")

        st.subheader("Free cloud quota (today)")
        st.progress(
            min(1.0, meter["frac_tokens_left"]),
            text=f"{meter['tokens_remaining']:,} / {meter['tokens_limit']:,} tokens left",
        )
        st.caption(
            f"Requests: {meter['requests_used']:,} / {meter['requests_limit']:,}"
        )
        if meter["frac_tokens_left"] < 0.1:
            st.warning("Free budget low — turn off AI judge / repair / A/B or use golden questions.")
        if meter["tokens_remaining"] <= 0:
            st.error("Daily free token budget exhausted for this app.")

        st.subheader("Session quality")
        st.metric("Pass rate", f"{pass_rate:.0f}%")
        st.metric(
            "Gated turns",
            f"{stats['pass']} PASS / {stats['total']}",
            delta=f"{stats['warn']} WARN · {stats['fail']} FAIL",
        )

        st.subheader("Red-team playground")
        attacks = load_red_team_prompts(limit=5)
        for a in attacks:
            if st.button(a["id"], key=f"rt_{a['id']}", use_container_width=True):
                process_turn(
                    a["question"],
                    use_judge,
                    enable_repair=enable_repair,
                    enable_ab=enable_ab,
                )
                st.rerun()

        st.divider()
        if st.button("Export turns CSV"):
            path = store.export_csv()
            st.success(f"Wrote {path}")
        if st.button("Clear chat UI"):
            st.session_state.messages = []
            st.rerun()

        st.caption("Golden example: *What is a flaky test, and why is it harmful in CI?*")
        st.caption("CI smoke: `python scripts/run_batch_gate.py`")

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
                ab = meta.get("ab") or {}
                if ab.get("enabled"):
                    st.caption(
                        f"A/B winner **{ab.get('winner')}** — "
                        f"A `{ab.get('model_a')}` {ab.get('status_a')} vs "
                        f"B `{ab.get('model_b')}` {ab.get('status_b')}"
                    )
                repair = meta.get("repair") or {}
                if repair.get("attempted"):
                    st.caption(
                        f"Repair: {repair.get('original_status')} → "
                        f"{repair.get('final_status')}"
                        + (" · improved" if repair.get("improved") else "")
                    )
                with st.expander("Gate details"):
                    st.write("**Reasons**")
                    for r in g.get("reasons") or []:
                        st.write(f"- {r}")
                    if repair.get("notes"):
                        st.write("**Repair notes**")
                        for n in repair["notes"]:
                            st.write(f"- {n}")
                    st.json(g.get("scores") or {})

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
