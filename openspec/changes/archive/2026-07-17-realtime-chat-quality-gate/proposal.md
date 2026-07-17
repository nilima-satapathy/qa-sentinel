## Why

Portfolio Projects 1–4 prove automation, UI testing, building RAG, and **batch** LLM evaluation. Recruiters still ask: *“How would quality work on a live GenAI product?”*

The previous Project 5 (CI-only quality gate) was abstract and hard to demo. A **realtime chatbot** where **every answer passes a quality gate** makes AI QA tangible: free-tier cloud models generate answers; rules + optional AI-as-judge score them; the UI shows pass/fail, reasons, latency, and free credits.

This showcases:
1. **Using AI** (chat SUT on free cloud tier)
2. **Gating AI** (quality pipeline on each turn)
3. **AI inside the gate** (optional LLM-as-judge)
4. Continuity with Project 4 golden/red-team assets

## What Changes

Greenfield product **QA Sentinel** (`qa-sentinel`):

- Live Streamlit chat against OpenAI-compatible free-tier models (default: Groq)
- Per-turn **quality gate** with layered scoring
- PASS / WARN / FAIL badge + reasons under every AI message
- Free-tier usage meter (requests/tokens remaining today)
- Turn history in SQLite
- Red-team / attack playground prompts for demos
- Offline **golden** fallback when no API key (matched questions)
- Docs, tests, and a short demo script for LinkedIn/interviews

## Capabilities

### New Capabilities
- `live-chat`: Realtime user→assistant chat via free cloud LLM or golden fallback
- `quality-gate`: Per-answer scoring (offline rules, golden match, optional AI judge)
- `free-tier-meter`: Track and display free cloud usage budget for demos
- `turn-history`: Persist turns, scores, latency, tokens for review
- `red-team-playground`: One-click adversarial prompts to demo safety gating

### Modified Capabilities
- (none — greenfield; no prior `openspec/specs/` source of truth)

## Impact

| Area | Impact |
|------|--------|
| New repo | `qa-sentinel` (local `C:\Users\admin\Code\qa-sentinel`) |
| Depends on | Project 4 `llm-eval-dashboard` (datasets + metrics patterns; clone or path) |
| Free tier | Groq (or similar) — chat ± optional judge call per turn |
| P4 code | Reuse, do not fork entire dashboard unless needed |
| Deploy | Optional later; localhost demo is enough for MVP |
| Out of scope | Multi-user auth, billing, multi-tenant SaaS, paid-only models |

## Better ideas (Stretch — not MVP blockers)

1. **Repair loop** — if WARN/FAIL, auto re-prompt model to fix issues and re-gate  
2. **A/B dual model** — two free models, gate both, pick winner  
3. **Session quality score** — rolling pass rate for the conversation  
4. **Batch CI smoke** — thin script reusing gate policy for golden regression  
5. **Side-by-side ungated vs gated** — teach why gates matter  

## Non-goals (MVP)

- Permanent cloud deploy requirement  
- Full DeepEval suite on every chat turn (too slow/costly for free tier)  
- Replacing Project 4 batch dashboard  
- Training or fine-tuning models  
