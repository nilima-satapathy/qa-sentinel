# QA Sentinel

**Portfolio Project 5** — Realtime software-testing AI chatbot with a **per-answer quality gate**.

Claude-style chat UI · Quality Gate **artifact** panel · Free-tier cloud (Groq) · Offline golden path  

Planned with [OpenSpec](https://openspec.dev/) · Built on [llm-eval-dashboard](https://github.com/nilima-satapathy/llm-eval-dashboard) (Project 4).

---

## What it does

```text
You ask a testing question
        ↓
Free-tier cloud LLM answers (Groq)  — or golden offline fallback
   (optional A/B: two models → gate both → pick winner)
        ↓
Quality gate scores the answer
  L1 offline policy · L2 golden match · L3 optional AI judge
   (optional repair: one rewrite + re-gate on WARN/FAIL)
        ↓
Chat + right-side Quality Gate artifact
  PASS / WARN / FAIL · L1–L3 layers · reasons · free-tier meter
```

**Showcase:** AI is used **as the product** (chat) **and inside the gate** (optional LLM-as-judge).

---

## Quick start

### Windows (PowerShell)

```powershell
git clone https://github.com/nilima-satapathy/qa-sentinel.git
cd qa-sentinel
powershell -File scripts/setup_harness.ps1

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
# Optional: add Groq key to .env for live cloud answers

pytest tests/ -q
python -m streamlit run app.py
```

### macOS / Linux

```bash
git clone https://github.com/nilima-satapathy/qa-sentinel.git
cd qa-sentinel
bash scripts/setup_harness.sh

python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

pytest tests/ -q
python -m streamlit run app.py
```

Open **http://localhost:8501**

### Without API key

Use a golden example:

> What is a flaky test, and why is it harmful in CI?

### With free Groq credits

```env
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_...
OPENAI_MODEL=llama-3.1-8b-instant
OPENAI_MODEL_B=llama-3.3-70b-versatile
```

**Sidebar:** AI-as-judge (L3), Repair loop, A/B dual models, red-team prompts.  
**Theme:** Light (Claude warm cream) or Dark (warm evening).

### Batch CI smoke (offline)

```bash
python scripts/run_batch_gate.py
python scripts/run_batch_gate.py --limit 5 --ids qa-001,qa-002
```

Exit code `1` if any case **FAIL**s.

---

## Architecture

| Layer | Role |
|-------|------|
| **Chat SUT** | Groq / OpenAI-compatible · golden fallback |
| **L1 gate** | Length, critical policy, domain fit (free) |
| **L2 gate** | Golden must_include + overlap when Q matches |
| **L3 gate** | Optional AI judge JSON score (free tier) |
| **Repair** | Optional one-shot rewrite on WARN/FAIL |
| **A/B** | Optional dual free models + gated winner |
| **Store** | SQLite turns + daily free-tier usage |
| **UI** | Claude-style chat + Quality Gate artifact panel |

OpenSpec (archived): `openspec/changes/archive/2026-07-17-realtime-chat-quality-gate/`  
Main specs: `openspec/specs/`

---

## Demo script (2 minutes)

1. Golden flaky-test question → **PASS** in chat + artifact panel  
2. Sidebar red-team button → refuse or **FAIL** if unsafe  
3. Toggle AI judge → show L3 reasons  
4. Point at free-tier meter + theme toggle  
5. (Optional) Repair · A/B two free models  

---

## Interview one-liner

> “I built a realtime testing assistant where every answer runs through a layered quality gate — offline rules, golden metrics, and optional AI-as-judge — on free-tier cloud models, with a Claude-style chat UI and a Quality Gate artifact panel.”

---

## Layout

```text
qa-sentinel/
├── app.py                 # Streamlit UI (Claude-style chat + artifact)
├── gate/policy.yaml
├── src/
│   ├── chat_client.py
│   ├── quality_gate.py
│   ├── repair.py
│   ├── store.py
│   └── paths.py
├── scripts/
│   ├── setup_harness.ps1 / .sh
│   └── run_batch_gate.py
├── tests/
├── openspec/
└── .streamlit/config.toml
```

## License

MIT — portfolio / learning project.
