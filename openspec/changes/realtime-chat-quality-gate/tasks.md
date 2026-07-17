## 1. Scaffold & dependency on Project 4

- [ ] 1.1 Confirm OpenSpec layout under `qa-sentinel/openspec/`
- [ ] 1.2 Add `README.md`, `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `.env.example`
- [ ] 1.3 Add `scripts/setup_harness.ps1` to clone `llm-eval-dashboard` into `vendor/`
- [ ] 1.4 Add `src/paths.py` (or `gate/paths.py`) resolving `LLM_EVAL_ROOT` / vendor path
- [ ] 1.5 Verify import of P4 `metrics_basic` and golden/red-team JSON loaders

## 2. Live chat SUT

- [ ] 2.1 Implement OpenAI-compatible `ChatClient` (reuse P4 patterns)
- [ ] 2.2 Wire env: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` (Groq defaults in `.env.example`)
- [ ] 2.3 Software-testing assistant system prompt
- [ ] 2.4 Golden fallback when no API key and question matches golden set
- [ ] 2.5 Unit/smoke test: mock HTTP or golden complete returns answer + latency

## 3. Quality gate engine (offline layers)

- [ ] 3.1 Define `gate/policy.yaml` thresholds (PASS/WARN/FAIL bands)
- [ ] 3.2 Implement L1 offline policy checks (length, safety, domain, injection heuristics)
- [ ] 3.3 Implement L2 golden match (must_include + overlap with live thresholds)
- [ ] 3.4 Implement aggregate status decision (pure function + unit tests)
- [ ] 3.5 Return structured `GateResult` (status, scores, reasons, layer details)

## 4. Streamlit realtime UI

- [ ] 4.1 Chat UI: user input → assistant message
- [ ] 4.2 Under each AI message: PASS/WARN/FAIL chip + scores + expandable reasons
- [ ] 4.3 Sidebar: model label, judge toggle (off by default), session stats
- [ ] 4.4 Surface API/rate-limit errors without crashing session
- [ ] 4.5 Local run: `python -m streamlit run app.py` (or `dashboard/app.py`)

## 5. Free-tier meter

- [ ] 5.1 Track tokens/requests for chat (+ judge when on) in SQLite or memory+SQLite
- [ ] 5.2 Configurable daily budgets in env/policy
- [ ] 5.3 Sidebar progress bar: free tokens/requests left today
- [ ] 5.4 Warn when budget low; block or warn when exhausted

## 6. Turn history

- [ ] 6.1 SQLite schema for turns (question, answer, status, scores, latency, tokens, model)
- [ ] 6.2 Persist every turn after gate
- [ ] 6.3 Simple history view or last-N list in UI
- [ ] 6.4 Optional CSV export for portfolio evidence

## 7. AI-as-judge (showcase AI in the gate)

- [ ] 7.1 Judge prompt returning strict JSON `{score, pass, reasons}`
- [ ] 7.2 Call only when sidebar toggle ON
- [ ] 7.3 Merge L3 into aggregate status; show “judge” reasons in UI
- [ ] 7.4 Document free-tier cost (second call) in README

## 8. Red-team playground

- [ ] 8.1 Load sample prompts from P4 `red_team_cases.json`
- [ ] 8.2 Sidebar buttons: inject attack prompt into chat input / send
- [ ] 8.3 Demo script: safe QA question → PASS; attack → FAIL or safe refusal PASS

## 9. Docs, tests, ship

- [ ] 9.1 Unit tests for gate decision pure functions (no network)
- [ ] 9.2 Integration test: golden-matched question offline path
- [ ] 9.3 README: architecture, free-tier setup, interview script
- [ ] 9.4 Career plan SPEC under `project-05-qa-sentinel` (or rename)
- [ ] 9.5 Optional: short LinkedIn demo video (30–45s)
- [ ] 9.6 `openspec validate realtime-chat-quality-gate`
- [ ] 9.7 After implementation: `openspec archive realtime-chat-quality-gate` (merge deltas into `openspec/specs/`)

## 10. Stretch (post-MVP)

- [ ] 10.1 Repair loop (one auto-rewrite + re-gate)
- [ ] 10.2 A/B dual free models + pick gated winner
- [ ] 10.3 Session quality score banner
- [ ] 10.4 Batch CI smoke script for golden subset
