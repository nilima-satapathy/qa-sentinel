"""Resolve project root and Project 4 harness root."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_HARNESS_REPO = "https://github.com/nilima-satapathy/llm-eval-dashboard.git"


def eval_root() -> Path:
    env = (os.getenv("LLM_EVAL_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    return (ROOT / "vendor" / "llm-eval-dashboard").resolve()


def _ensure_vendor_harness(er: Path) -> None:
    """Clone Project 4 harness if missing (Streamlit Cloud / Docker / fresh clone)."""
    marker = er / "src" / "metrics_basic.py"
    if marker.exists():
        return
    er.parent.mkdir(parents=True, exist_ok=True)
    if er.exists():
        # Incomplete checkout — remove and re-clone
        import shutil

        shutil.rmtree(er, ignore_errors=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", _HARNESS_REPO, str(er)],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def ensure_import_paths() -> Path:
    er = eval_root()
    # Only auto-clone the default vendor path (not a custom LLM_EVAL_ROOT)
    if not (os.getenv("LLM_EVAL_ROOT") or "").strip():
        try:
            _ensure_vendor_harness(er)
        except Exception as exc:  # noqa: BLE001
            raise FileNotFoundError(
                f"Project 4 harness not found at {er} and auto-clone failed: {exc}\n"
                "Run: bash scripts/setup_harness.sh\n"
                "Or set LLM_EVAL_ROOT to your llm-eval-dashboard path."
            ) from exc
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
