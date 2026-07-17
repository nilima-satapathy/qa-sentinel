## Context

Greenfield portfolio app. Project 4 provides offline metrics and golden/red-team datasets. This design defines a **live chat product** with a **per-turn quality gate**, optimized for free-tier cloud models (Groq OpenAI-compatible API).

## Goals / Non-Goals

**Goals:**
- Realtime chat UX (Streamlit) with free-tier LLM answers
- Every AI answer scored before presentation completes
- Clear PASS / WARN / FAIL + human-readable reasons
- Free-credit visibility so demos stay intentional
- Offline demo path without API keys (golden match / mock)
- Showcase AI-as-judge as optional layer (AI *inside* the gate)
- Reuse Project 4 metrics and datasets where possible

**Non-Goals:**
- Multi-tenant auth, SSO, production SLAs
- Guaranteeing high pass rates on free small models (expect WARN/FAIL demos)
- Full 42-case batch run on every chat message
- Paid OpenAI as default
- Permanent deploy as a ship requirement

## Decisions

### D1 — Product name & repo
- **Name:** QA Sentinel  
- **Path:** `C:\Users\admin\Code\qa-sentinel`  
- **GitHub (later):** `nilima-satapathy/qa-sentinel`  
- Separate from P4; **depends on** P4 via `vendor/llm-eval-dashboard` or `LLM_EVAL_ROOT`

### D2 — Chat SUT
- OpenAI-compatible Chat Completions (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`)  
- Default demo: Groq `llama-3.1-8b-instant`  
- System prompt: software-testing assistant (align with P4)  
- Fallback: if no key, attempt golden lookup by question; else polite “configure free API” message

### D3 — Layered quality gate (core showcase)

| Layer | Always? | Cost | Role |
|-------|---------|------|------|
| L1 Offline policy | Yes | Free | Length, safety phrases, domain/out-of-scope, injection cues |
| L2 Golden match | If Q matches golden case | Free | must_include + reference_overlap (live thresholds) |
| L3 AI judge | Optional toggle | 1 free-tier call | JSON score + pass + reasons |

**Aggregate status:**
- **FAIL** if L1 critical policy fail OR (L2 present and hard fail) OR (L3 on and judge fails hard)
- **WARN** if borderline scores (e.g. low domain fit / mid judge score)
- **PASS** otherwise

Exact thresholds live in `gate/policy.yaml` (tunable without code changes).

### D4 — Free-tier strategy
- Track tokens/requests for **this app’s** openai backend calls (chat + judge)  
- Sidebar progress: remaining daily free tokens (configurable defaults like P4)  
- Default **judge OFF** to save credits; enable for interview wow  
- Optional small delay if rate-limited (surface error clearly)

### D5 — Persistence
- SQLite `data/turns.sqlite3`: turn_id, question, answer, gate_status, scores JSON, latency_ms, tokens, model, created_at  
- Optional export CSV for portfolio evidence

### D6 — UI (Streamlit)
- Main: chat history; under each assistant message: status chip + scores + expand reasons  
- Sidebar: model, judge on/off, free-tier bar, session pass rate, attack example buttons  
- Red-team playground: inject fixed prompts from P4 red-team set

### D7 — Reuse from Project 4
- Import `metrics_basic` (must_include, overlap, must_not)  
- Load golden + red-team JSON for L2 and playground  
- Mirror OpenAI-compatible client pattern from `target_app.py` (thin copy or path import)

### D8 — Testing strategy
- Unit: gate decision pure functions (no network)  
- Integration: golden-matched turn scores offline  
- Manual: live Groq smoke with 2–3 questions  
- Optional: batch script later for CI golden smoke (stretch)

## Architecture

```text
User ──► Streamlit Chat UI
              │
              ├─► ChatClient.complete(q) ──► Groq (free) ──► answer, latency, tokens
              │
              └─► QualityGate.evaluate(q, answer)
                       ├─ L1 offline policy
                       ├─ L2 golden match (if any)
                       └─ L3 AI judge (optional)
              │
              ▼
         TurnStore.save(...)
              │
              ▼
         UI: answer + PASS/WARN/FAIL + free-tier meter
```

## Risks / Trade-offs

| Risk | Trade-off / mitigation |
|------|------------------------|
| Free model weak answers → many FAILs | Use WARN band; looser L2 thresholds; demo golden path |
| Double call (judge) burns free tier | Judge off by default; meter + quick mode |
| Rate limits (429) | Clear error, retry guidance, don’t crash UI |
| Scope creep (repair/A/B) | Stretch only after MVP M1–M4 |
| Vendor path missing | setup script clones P4; fail with clear message |

## Stretch (post-MVP)

1. **Repair loop** — on WARN/FAIL, one auto-rewrite attempt + re-gate  
2. **A/B models** — two free models, gate both, display winner  
3. **Session quality score** — rolling % PASS  
4. **CI smoke** — `scripts/run_batch_gate.py` on golden subset  
5. **Gated vs ungated toggle** for teaching demos  
