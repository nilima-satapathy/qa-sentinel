# QA Sentinel

**Portfolio Project 5** — Realtime software-testing AI chatbot with a **per-answer quality gate**.

Planned with **[OpenSpec](https://openspec.dev/)** (spec-driven development).

## Product idea

User asks a question → free-tier cloud LLM answers (e.g. Groq) → **quality gate** scores the answer → UI shows **PASS / WARN / FAIL**, reasons, latency, tokens, and free-credit remaining.

## OpenSpec plan (source of truth for implementation)

```text
openspec/
├── config.yaml                          # project context for AI
├── specs/                               # main specs (after archive)
└── changes/realtime-chat-quality-gate/  # active change
    ├── proposal.md                      # why / what
    ├── design.md                        # architecture decisions
    ├── tasks.md                         # implementation checklist
    └── specs/                           # requirement deltas
        ├── live-chat/
        ├── quality-gate/
        ├── free-tier-meter/
        ├── turn-history/
        └── red-team-playground/
```

### Useful commands

```powershell
cd C:\Users\admin\Code\qa-sentinel
openspec list
openspec show realtime-chat-quality-gate
openspec validate realtime-chat-quality-gate
openspec status --change realtime-chat-quality-gate
```

### After you approve the plan

Implementation follows `openspec/changes/realtime-chat-quality-gate/tasks.md`  
(or tell the agent: apply the OpenSpec change `realtime-chat-quality-gate`).

## Depends on Project 4

[llm-eval-dashboard](https://github.com/nilima-satapathy/llm-eval-dashboard) — golden set, red-team cases, offline metrics patterns.

## Free tier

Default: Groq OpenAI-compatible API (`llama-3.1-8b-instant`).  
AI-as-judge is optional (second free call). Offline golden path works without keys.

## Status

**Planning complete (OpenSpec).** Implementation not started yet.
