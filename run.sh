#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Prefer 3.13 — system 3.14 lacks wheels for pydantic/orjson today
PY=python3.13
command -v "$PY" >/dev/null || PY=python3
if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -U pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
exec uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8787
