"""
Community Pulse — Bot de Discord.

Dos modos de operación complementarios:

1. **Ingesta en vivo** (``on_message``): cada mensaje que publica un miembro
   se normaliza y se envía al webhook de la API (JobWorker → pipeline →
   dashboard). Es el flujo continuo; los resultados se ven en el dashboard.

2. **Comando ``!pulse``**: procesa bajo demanda el historial reciente del
   canal y publica un resumen inline en el propio canal.

Configuración (variables de entorno, ver ``.env.example``):
    DISCORD_BOT_TOKEN           → token del bot (obligatorio)
    WEBHOOK_URL                 → URL de la API (default http://localhost:8000/webhook)
    DISCORD_REACT_ON_INGEST     → "1" para reaccionar 👀 a cada mensaje ingerido
    COMMUNITYLAB_LLM_BACKEND    → ``rule_based`` para demo offline sin API key
    (credenciales OCI opcionales para persistir en Object Storage)

Ejecutar:
    python -m src.bot.discord_bot

Responsable: Backend Developer
"""

import logging
import os

import httpx
from dotenv import load_dotenv

from src.bot.pulse import (
    DEFAULT_LIMIT,
    build_batch_from_messages,
    format_pulse_result,
)
from src.orchestration.pipeline import CommunityPulsePipeline
from src.utils.llm_client import create_llm_client
from src.oci.client import create_oci_storage

load_dotenv()

log = logging.getLogger("community_pulse.bot")

DEFAULT_WEBHOOK_URL = "http://localhost:8000/webhook"
DEFAULT_PERIODO = "Discord_live"


def _import_discord():
    """Importa discord.py de forma perezosa, con mensaje de error claro."""
    try:
        import discord
        from discord.ext import commands

        return discord, commands
    except ImportError as e:
        raise ImportError(
            "Instala discord.py: pip install discord.py"
        ) from e


# ----------------------------------------------------------------------
# Ingesta en vivo
# ----------------------------------------------------------------------
async def ingest_message_to_webhook(
    message,
    webhook_url: str,
    periodo: str = DEFAULT_PERIODO,
    http_client=None,
) -> dict:
    """
    Normaliza un mensaje de Discord y lo envía al webhook de la API.

    Retorna un dict con el resultado:
        {"ingested": True, "job_id": "..."}   → encolado OK
        {"ingested": False, "reason": ...}    → sin contenido (bots/comandos)

    ``http_client`` es inyectable para tests (objeto con ``post`` async).
    """
    payload = build_batch_from_messages([message], periodo)
    if not payload["interacciones"]:
        return {"ingested": False, "reason": "sin_contenido"}

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
        return {"ingested": True, "job_id": resp.json().get("job_id")}
    finally:
        if owns_client:
            await client.aclose()


# ----------------------------------------------------------------------
# Construcción del bot
# ----------------------------------------------------------------------
def create_bot(
    command_prefix: str = "!",
    llm_client=None,
    oci_storage=None,
    periodo: str = DEFAULT_PERIODO,
    webhook_url: str = None,
    react_on_ingest: bool = None,
):
    """
    Construye y configura el bot (comando ``!pulse`` + ingesta en vivo).

    ``llm_client`` y ``oci_storage`` se resuelven por configuración si no se
    inyectan (permite tests con clientes falsos).
    """
    discord, commands = _import_discord()

    if llm_client is None:
        llm_client = create_llm_client()
    if oci_storage is None:
        oci_storage = create_oci_storage()
    pipeline = CommunityPulsePipeline(llm_client, oci_storage)

    webhook_url = webhook_url or os.getenv("WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
    if react_on_ingest is None:
        react_on_ingest = os.getenv("DISCORD_REACT_ON_INGEST", "0") == "1"

    # La ingesta en vivo lee ``message.content`` en ``on_message``, que solo
    # llega poblado si está habilitado el "Message Content Intent" (privilegiado)
    # tanto en el código como en el Discord Developer Portal.
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=command_prefix, intents=intents)

    # Estado compartido entre los handlers
    bot._webhook_url = webhook_url
    bot._periodo = periodo
    bot._react_on_ingest = react_on_ingest

    # ------------------------------------------------------------------
    # Comando bajo demanda: !pulse
    # ------------------------------------------------------------------
    @bot.command(name="pulse")
    async def pulse(ctx, limite: int = DEFAULT_LIMIT):
        """Procesa el historial reciente del canal y publica el resumen.

        Uso: ``!pulse`` o ``!pulse 25`` (límite entre 1 y 200 mensajes).
        """
        limite = max(1, min(limite, 200))
        async with ctx.typing():
            messages = [m async for m in ctx.channel.history(limit=limite)]
            payload = build_batch_from_messages(messages, periodo)
            if not payload["interacciones"]:
                await ctx.send("🤷 No encontré mensajes para analizar.")
                return
            resultado = await pipeline.process(payload)
            resumen = format_pulse_result(resultado)
        await ctx.send(resumen)

    # ------------------------------------------------------------------
    # Ingesta en vivo: on_message → normalizar → POST /webhook
    # ------------------------------------------------------------------
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # Procesa comandos (ej. !pulse) y luego intenta ingerir el mensaje.
        await bot.process_commands(message)
        await _live_ingest(bot, message)

    async def _live_ingest(bot, message):
        try:
            resultado = await ingest_message_to_webhook(
                message, bot._webhook_url, bot._periodo
            )
            if resultado.get("ingested") and bot._react_on_ingest:
                await message.add_reaction("👀")
        except httpx.HTTPError as exc:
            log.warning("Webhook no disponible para mensaje %s: %s", message.id, exc)
        except Exception as exc:  # noqa: BLE001 — no romper el loop del bot
            log.exception("Error inesperado ingiriendo mensaje %s: %s", message.id, exc)

    @bot.event
    async def on_ready():
        print(f"✅ Community Pulse bot conectado como {bot.user}")

    return bot


def main():
    """Punto de entrada: ejecuta el bot con el token de ``.env``."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Configurá DISCORD_BOT_TOKEN en .env (ver .env.example)"
        )
    bot = create_bot()
    bot.run(token)


if __name__ == "__main__":
    main()
