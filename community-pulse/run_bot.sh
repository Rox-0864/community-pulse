#!/usr/bin/env bash
# Community Pulse — corre el bot de Discord (ingesta en vivo + !pulse).
# Uso: ./run_bot.sh  (requiere la API corriendo en WEBHOOK_URL)
set -e
cd "$(dirname "$0")"
source venv/bin/activate
python -m src.bot.discord_bot
