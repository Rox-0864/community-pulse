"""Tests de la ingesta en vivo del bot (on_message → webhook).

Cubren ``ingest_message_to_webhook`` de ``src/bot/discord_bot.py`` con un
cliente HTTP falso. No requieren token, conexión a Discord ni la API real.
"""

import pytest

from src.bot.discord_bot import ingest_message_to_webhook


# ----------------------------------------------------------------------
# Fakes tipo discord.Message
# ----------------------------------------------------------------------
class _FakeAuthor:
    def __init__(self, name, bot=False):
        self.name = name
        self.bot = bot


class _FakeChannel:
    def __init__(self, name):
        self.name = name


class _FakeMessage:
    def __init__(self, content, author="Ana", channel="general", bot=False):
        self.content = content
        self.author = _FakeAuthor(author, bot) if isinstance(author, str) else author
        self.channel = _FakeChannel(channel) if isinstance(channel, str) else channel
        self.created_at = None


# ----------------------------------------------------------------------
# Fake HTTP client (captura la llamada)
# ----------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, status_code=202, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class _FakeHTTPClient:
    def __init__(self, response=None):
        self._response = response or _FakeResponse()
        self.posted = []

    async def post(self, url, json=None):
        self.posted.append((url, json))
        return self._response


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ingest_happy_path_posts_payload():
    http = _FakeHTTPClient(response=_FakeResponse(json_data={"job_id": "abc123"}))
    resultado = await ingest_message_to_webhook(
        _FakeMessage("hola comunidad", "Ana", "#general"),
        webhook_url="http://localhost:8000/webhook",
        http_client=http,
    )

    assert resultado["ingested"] is True
    assert resultado["job_id"] == "abc123"

    url, payload = http.posted[0]
    assert url == "http://localhost:8000/webhook"
    assert payload["origen_comunidad"] == "discord"
    assert payload["periodo_referencia"] == "Discord_live"
    assert len(payload["interacciones"]) == 1
    assert payload["interacciones"][0]["texto"] == "hola comunidad"
    assert payload["interacciones"][0]["autor"] == "Ana"
    assert payload["interacciones"][0]["canal"] == "#general"


@pytest.mark.asyncio
async def test_ingest_skips_bot_message_without_posting():
    http = _FakeHTTPClient()
    resultado = await ingest_message_to_webhook(
        _FakeMessage("soy un bot", bot=True),
        webhook_url="http://localhost:8000/webhook",
        http_client=http,
    )

    assert resultado == {"ingested": False, "reason": "sin_contenido"}
    assert http.posted == []


@pytest.mark.asyncio
async def test_ingest_skips_command_prefix():
    http = _FakeHTTPClient()
    resultado = await ingest_message_to_webhook(
        _FakeMessage("!pulse", "Ana"),
        webhook_url="http://localhost:8000/webhook",
        http_client=http,
    )

    assert resultado == {"ingested": False, "reason": "sin_contenido"}
    assert http.posted == []
