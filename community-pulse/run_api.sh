#!/usr/bin/env bash
# Community Pulse — levanta la API (uvicorn) en el puerto 8000.
# Uso: ./run_api.sh
set -e
cd "$(dirname "$0")"
source venv/bin/activate
uvicorn src.api.endpoints:app --host 0.0.0.0 --port 8000
