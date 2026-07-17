#!/usr/bin/env bash
# Clone Project 4 eval harness into vendor/ (metrics + golden/red-team datasets)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor/llm-eval-dashboard"

if [[ -f "$VENDOR/src/metrics_basic.py" ]]; then
  echo "Harness OK: $VENDOR"
  exit 0
fi

mkdir -p "$ROOT/vendor"
rm -rf "$VENDOR"

if [[ -n "${LLM_EVAL_ROOT:-}" && -f "${LLM_EVAL_ROOT}/src/metrics_basic.py" ]]; then
  echo "Copying harness from LLM_EVAL_ROOT=$LLM_EVAL_ROOT"
  cp -R "$LLM_EVAL_ROOT" "$VENDOR"
  rm -rf "$VENDOR/.venv" "$VENDOR/data" "$VENDOR/reports" "$VENDOR/.pytest_cache" "$VENDOR/.git" || true
else
  git clone --depth 1 https://github.com/nilima-satapathy/llm-eval-dashboard.git "$VENDOR"
fi

echo "Harness ready: $VENDOR"
