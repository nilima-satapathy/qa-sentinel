from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup harness path for tests
from qasentinel.paths import ensure_import_paths  # noqa: E402

try:
    ensure_import_paths()
except FileNotFoundError:
    # Try auto local path
    import os

    local = Path(r"C:\Users\admin\Code\llm-eval-dashboard")
    if (local / "src" / "metrics_basic.py").exists():
        os.environ["LLM_EVAL_ROOT"] = str(local)
        ensure_import_paths()
