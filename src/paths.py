"""Resolve project root and Project 4 harness root."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def eval_root() -> Path:
    env = (os.getenv("LLM_EVAL_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return (ROOT / "vendor" / "llm-eval-dashboard").resolve()


def ensure_import_paths() -> Path:
    er = eval_root()
    for p in (str(ROOT), str(er)):
        if p not in sys.path:
            sys.path.insert(0, p)
    if not (er / "src" / "metrics_basic.py").exists():
        raise FileNotFoundError(
            f"Project 4 harness not found at {er}.\n"
            "Run: powershell -File scripts/setup_harness.ps1\n"
            "Or set LLM_EVAL_ROOT to your llm-eval-dashboard path."
        )
    return er
