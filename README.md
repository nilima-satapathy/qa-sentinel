# QA Sentinel

**Portfolio Project 5** — Realtime software-testing AI chatbot with a **per-answer quality gate**.

Planned with [OpenSpec](https://openspec.dev/) · Built on [llm-eval-dashboard](https://github.com/nilima-satapathy/llm-eval-dashboard) (Project 4).

---

## What it does

```text
You ask a testing question
        ↓
Free-tier cloud LLM answers (Groq)  — or golden offline fallback
        ↓
Quality gate scores the answer
  L1 offline policy · L2 golden match · L3 optional AI judge
        ↓
UI shows answer + 🟢 PASS / 🟡 WARN / 🔴 FAIL + reasons
        + free-credit meter + session quality
```

**Showcase:** AI is used **as the product** (chat) **and inside the gate** (optional LLM-as-judge).

---

## Quick start

```powershell
cd C:\Users\admin\Code\qa-sentinel
powershell -File scripts/setup_harness.ps1

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
# Optional: add Groq key to .env for live cloud answers

pytest tests/ -q
python -m streamlit run app.py
```

Open **http://localhost:8501**

### Without API key
Use the golden example question:

> What is a flaky test, and why is it harmful in CI?

### With free Groq credits
```env
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_...
OPENAI_MODEL=llama-3.1-8b-instant
```

Toggle **AI-as-judge (L3)** in the sidebar for a second free-tier call.

---

## Architecture

| Layer | Role |
|-------|------|
| **Chat SUT** | Groq / OpenAI-compatible · golden fallback |
| **L1 gate** | Length, critical policy, domain fit (free) |
| **L2 gate** | Golden must_include + overlap when Q matches |
| **L3 gate** | Optional AI judge JSON score (free tier) |
| **Store** | SQLite turns + daily free-tier usage |

OpenSpec plan: `openspec/changes/realtime-chat-quality-gate/`

---

## Demo script (2 minutes)

1. Golden question → **PASS** badge  
2. Sidebar red-team button → refuse or **FAIL** if unsafe  
3. Toggle AI judge → show L3 reasons  
4. Point at free-tier meter  

---

## Interview one-liner

> “I built a realtime testing assistant chatbot where every answer runs through a quality gate — offline rules, golden metrics, and optional AI-as-judge — on free-tier cloud models.”

---

## Layout

```text
qa-sentinel/
├── app.py                 # Streamlit UI
├── gate/policy.yaml
├── src/
│   ├── chat_client.py
│   ├── quality_gate.py
│   ├── store.py
│   └── paths.py
├── tests/
├── openspec/              # Spec-driven plan
└── scripts/setup_harness.ps1
```
