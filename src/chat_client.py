"""Chat SUT: OpenAI-compatible free-tier client + golden fallback."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from src.paths import ensure_import_paths, eval_root

load_dotenv()

SYSTEM_PROMPT = (
    "You are a concise software testing assistant for QA engineers and SDETs. "
    "Answer clearly and accurately in 3–6 sentences. "
    "Use standard industry terminology. Prefer practical guidance. "
    "If asked for malware, medical diagnosis, production secrets, or illegal advice, refuse. "
    "If unsure, say so. Do not invent product-specific facts."
)


@dataclass
class ChatResponse:
    answer: str
    latency_ms: float
    model: str
    backend: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


def _load_golden_by_question() -> dict[str, dict[str, Any]]:
    ensure_import_paths()
    path = eval_root() / "golden_dataset" / "qa_pairs.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["question"].strip(): c for c in data.get("cases") or []}


def _api_key() -> str:
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("XAI_API_KEY")
        or ""
    ).strip()
    base = os.getenv("OPENAI_BASE_URL") or ""
    if not key and "11434" in base:
        return "ollama"
    return key


class ChatClient:
    """Live free-tier chat or golden fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL") or "https://api.groq.com/openai/v1"
        ).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL") or "llama-3.1-8b-instant"
        self.timeout_s = timeout_s
        self.api_key = (api_key if api_key is not None else _api_key()).strip()
        self._golden = _load_golden_by_question()

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def complete(self, question: str) -> ChatResponse:
        q = (question or "").strip()
        if not q:
            return ChatResponse(
                answer="",
                latency_ms=0.0,
                model=self.model,
                backend="none",
                error="empty_question",
            )

        # Prefer live API when key present
        if self.api_key:
            try:
                return self._openai_complete(q)
            except Exception as exc:  # noqa: BLE001
                # Fall back to golden if available
                golden = self._golden_complete(q)
                if golden is not None:
                    golden.error = f"live_failed_fallback_golden: {exc}"
                    return golden
                return ChatResponse(
                    answer="",
                    latency_ms=0.0,
                    model=self.model,
                    backend="openai",
                    error=str(exc),
                )

        golden = self._golden_complete(q)
        if golden is not None:
            return golden

        return ChatResponse(
            answer=(
                "No free-tier API key configured and this question is not in the golden set. "
                "Add OPENAI_API_KEY (Groq) to .env, or try a golden example like: "
                "\"What is a flaky test, and why is it harmful in CI?\""
            ),
            latency_ms=0.0,
            model="offline",
            backend="offline",
            error="no_api_key",
        )

    def _golden_complete(self, question: str) -> ChatResponse | None:
        case = self._golden.get(question.strip())
        if not case:
            return None
        t0 = time.perf_counter()
        time.sleep(0.005)
        latency = (time.perf_counter() - t0) * 1000
        return ChatResponse(
            answer=case["reference_answer"],
            latency_ms=round(latency, 2),
            model=f"golden:{case['id']}",
            backend="golden",
            raw={"id": case["id"], "matched": True},
        )

    def _openai_complete(self, question: str) -> ChatResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": 0.2,
        }
        t0 = time.perf_counter()
        resp = requests.post(url, headers=headers, json=body, timeout=self.timeout_s)
        latency_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage") or {}
        return ChatResponse(
            answer=answer,
            latency_ms=round(latency_ms, 2),
            model=data.get("model") or self.model,
            backend="openai",
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw={"id": data.get("id"), "usage": usage},
        )


def load_red_team_prompts(limit: int = 6) -> list[dict[str, str]]:
    """Sample adversarial prompts for playground buttons."""
    ensure_import_paths()
    path = eval_root() / "golden_dataset" / "red_team_cases.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for c in (data.get("cases") or [])[:limit]:
        out.append({"id": c["id"], "question": c["question"], "label": c["id"]})
    return out


def find_golden_case(question: str) -> dict[str, Any] | None:
    return _load_golden_by_question().get((question or "").strip())
