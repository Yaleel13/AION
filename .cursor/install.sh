#!/usr/bin/env bash
# Idempotent repository bootstrap for the AION dev environment.
# Sets up the Python FastAPI backend (aion/) and the Next.js frontend (app/).
set -euo pipefail

cd "$(dirname "$0")/.."

# System dependency required to create Python virtualenvs on this base image.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3.12-venv
fi

# Python backend: isolated virtualenv with runtime + test dependencies.
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Next.js frontend dependencies.
npm ci

# Provide a local .env (mock mode, no real secrets) if one is not present.
# Real credentials should be supplied via Cursor secrets, not this file.
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "AION environment bootstrap complete."
