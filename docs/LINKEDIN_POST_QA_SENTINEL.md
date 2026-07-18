# LinkedIn post — QA Sentinel (Project 5)

## Option A — Main post (recommended)

---

How do you quality-gate a **live** GenAI answer — not just a batch report after the fact?

I built **QA Sentinel**: a realtime software-testing chatbot where **every AI answer** runs through a layered quality gate.

**What it does**
You ask a testing question → free-tier cloud model answers (or offline golden fallback) → the gate scores the answer before you trust it.

**The gate (interview one-liner)**
- **L1** — offline policy: length, safety blocklists, domain fit (always free)
- **L2** — golden metrics when free-tier credits are exhausted
- **L3** — LLM-as-judge for **factual accuracy** while free tier is working

**Also shipped**
Red-team playground · free-tier usage meter · repair / A/B stretch · pytest + GitHub Actions CI · Claude-style UI with a Quality Gate artifact panel

This sits on top of my **LLM Evaluation Dashboard** (Project 4) — same golden/red-team mindset, now as a **live product quality pattern**.

I’m targeting **AI QA / GenAI SDET / LLM Evaluation** roles — happy to walk through tradeoffs (when offline rules beat a judge, when free-tier budget changes the gate strategy).

**Repo:** https://github.com/nilima-satapathy/qa-sentinel  
**Portfolio:** https://portfolio-gamma-three-dr2ocwjp91.vercel.app/

#AIQA #GenAI #LLMEvaluation #QualityEngineering #SDET #SoftwareTesting #Python #Streamlit #OpenToWork

---

## Option B — Shorter (if you prefer tight posts)

---

Built **QA Sentinel** — a software-testing AI chatbot where **every answer is quality-gated**.

L1 offline policy · L2 golden metrics (when free tier is exhausted) · L3 LLM-as-judge for factual accuracy · red-team playground · free-tier meter · CI

Classic QA experience (Microsoft / Google products via HCL) + hands-on GenAI quality systems.

GitHub → https://github.com/nilima-satapathy/qa-sentinel

#AIQA #LLMEvaluation #QualityEngineering #GenAI

---

## Option C — Caption if you attach a video only

---

45 seconds: realtime chat → Quality Gate artifact (PASS/WARN/FAIL) → L1/L2/L3 reasons → free-tier meter.

QA Sentinel — live GenAI quality gate for a testing assistant.  
Full write-up + code: github.com/nilima-satapathy/qa-sentinel

#AIQA #GenAI #LLMEvaluation

---

## Posting tips

1. Attach the demo video (mute OK; add captions if you can).
2. First comment: link Project 4 (llm-eval-dashboard) as “batch eval → online gate.”
3. Tag lightly (3–6 hashtags max performs better than 15).
4. Post weekday morning IST or when your network is active.
