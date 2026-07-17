## 1. Scaffold & dependency on Project 4

- [x] 1.1 Confirm OpenSpec layout under `qa-sentinel/openspec/`
- [x] 1.2 Add `README.md`, `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `.env.example`
- [x] 1.3 Add `scripts/setup_harness.ps1` to clone `llm-eval-dashboard` into `vendor/`
- [x] 1.4 Add `src/paths.py` (or `gate/paths.py`) resolving `LLM_EVAL_ROOT` / vendor path
- [x] 1.5 Verify import of P4 `metrics_basic` and golden/red-team JSON loaders

## 2. Live chat SUT

- [x] 2.1 Implement OpenAI-compatible `ChatClient` (reuse P4 patterns)
- [x] 2.2 Wire env: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` (Groq defaults in `.env.example`)
- [x] 2.3 Software-testing assistant system prompt
- [x] 2.4 Golden fallback when no API key and question matches golden set
- [x] 2.5 Unit/smoke test: mock HTTP or golden complete returns answer + latency

## 3. Quality gate engine (offline layers)

- [x] 3.1 Define `gate/policy.yaml` thresholds (PASS/WARN/FAIL bands)
- [x] 3.2 Implement L1 offline policy checks (length, safety, domain, injection heuristics)
- [x] 3.3 Implement L2 golden match (must_include + overlap with live thresholds)
- [x] 3.4 Implement aggregate status decision (pure function + unit tests)
- [x] 3.5 Return structured `GateResult` (status, scores, reasons, layer details)

## 4. Streamlit realtime UI

- [x] 4.1 Chat UI: user input → assistant message
- [x] 4.2 Under each AI message: PASS/WARN/FAIL chip + scores + expandable reasons
- [x] 4.3 Sidebar: model label, judge toggle (off by default), session stats
- [x] 4.4 Surface API/rate-limit errors without crashing session
- [x] 4.5 Local run: `python -m streamlit run app.py` (or `dashboard/app.py`)

## 5. Free-tier meter

- [x] 5.1 Track tokens/requests for chat (+ judge when on) in SQLite or memory+SQLite
- [x] 5.2 Configurable daily budgets in env/policy
- [x] 5.3 Sidebar progress bar: free tokens/requests left today
- [x] 5.4 Warn when budget low; block or warn when exhausted

## 6. Turn history

- [x] 6.1 SQLite schema for turns (question, answer, status, scores, latency, tokens, model)
- [x] 6.2 Persist every turn after gate
- [x] 6.3 Simple history view or last-N list in UI
- [x] 6.4 Optional CSV export for portfolio evidence

## 7. AI-as-judge (showcase AI in the gate)

- [x] 7.1 Judge prompt returning strict JSON `{score, pass, reasons}`
- [x] 7.2 Call only when sidebar toggle ON
- [x] 7.3 Merge L3 into aggregate status; show “judge” reasons in UI
- [x] 7.4 Document free-tier cost (second call) in README

## 8. Red-team playground

- [x] 8.1 Load sample prompts from P4 `red_team_cases.json`
- [x] 8.2 Sidebar buttons: inject attack prompt into chat input / send
- [x] 8.3 Demo script: safe QA question → PASS; attack → FAIL or safe refusal PASS

## 9. Docs, tests, ship

- [x] 9.1 Unit tests for gate decision pure functions (no network)
- [x] 9.2 Integration test: golden-matched question offline path
- [x] 9.3 README: architecture, free-tier setup, interview script
- [x] 9.4 Career plan SPEC under `project-05-qa-sentinel` (or rename)
- [ ] 9.5 Optional: short LinkedIn demo video (30–45s) — after GitHub public URL
- [x] 9.6 `openspec validate realtime-chat-quality-gate`
- [x] 9.7 After implementation: `openspec archive realtime-chat-quality-gate` (merge deltas into `openspec/specs/`)

## 10. Stretch (post-MVP)

- [x] 10.1 Repair loop (one auto-rewrite + re-gate)
- [x] 10.2 A/B dual free models + pick gated winner
- [x] 10.3 Session quality score banner
- [x] 10.4 Batch CI smoke script for golden subset
