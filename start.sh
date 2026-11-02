#!/usr/bin/env bash
# Mac / Linux starter
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "EstateHawk: http://localhost:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
