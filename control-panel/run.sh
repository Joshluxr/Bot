#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
pip install -q -r requirements.txt
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}" --reload
