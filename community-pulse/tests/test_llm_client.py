"""Tests de la factory create_llm_client() y del cliente Groq.

Verifican la cadena de fallback multi-proveedor sin hacer llamadas de red
(los clientes Gemini/Groq se construyen de forma lazy, sin tocar la API).
"""

from src.utils.llm_client import (
    create_llm_client,
    FallbackLLMClient,
    GeminiClient,
    GroqClient,
)
from src.utils.rule_based import RuleBasedClient


def test_factory_con_solo_groq(monkeypatch):
    """Con solo GROQ_API_KEY, la factory devuelve GroqClient → rule_based."""
    monkeypatch.delenv("COMMUNITYLAB_LLM_BACKEND", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    client = create_llm_client()

    assert isinstance(client, FallbackLLMClient)
    assert isinstance(client._primary, GroqClient)
    assert client._primary.model == "openai/gpt-oss-120b"
    assert isinstance(client._fallback, RuleBasedClient)


def test_factory_cadena_gemini_groq(monkeypatch):
    """Con Gemini y Groq, la cadena es Gemini → Groq → rule_based."""
    monkeypatch.delenv("COMMUNITYLAB_LLM_BACKEND", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gem_test")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    client = create_llm_client()

    # Primario: Gemini. Su fallback: otra cadena Groq → rule_based.
    assert isinstance(client, FallbackLLMClient)
    assert isinstance(client._primary, GeminiClient)
    assert isinstance(client._fallback, FallbackLLMClient)
    assert isinstance(client._fallback._primary, GroqClient)
    assert isinstance(client._fallback._fallback, RuleBasedClient)


def test_groq_model_configurable_por_env(monkeypatch):
    """GROQ_MODEL en el entorno pisa el default."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    client = GroqClient()
    assert client.model == "openai/gpt-oss-20b"


# ----------------------------------------------------------------------
# Reintentos ante errores transitorios (429/503)
# ----------------------------------------------------------------------
class _Respuesta:
    """Respuesta mínima con .choices[0].message.content."""

    def __init__(self, payload: dict):
        import json

        class _Msg:
            def __init__(self, c):
                self.content = c

        class _Choice:
            def __init__(self, c):
                self.message = _Msg(c)

        self.choices = [_Choice(json.dumps(payload))]


def test_gemini_client_forza_json_mode(monkeypatch):
    """response_format=json_object fuerza response_mime_type en Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

    client = GeminiClient()
    capturado = {}

    class FakeResponse:
        text = '{"sentiment": "neutral"}'

    def fake_generate_content(**kwargs):
        capturado.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(client._client.models, "generate_content", fake_generate_content)

    resp = client._create(
        messages=[
            {"role": "system", "content": "Analiza el sentimiento."},
            {"role": "user", "content": "texto de prueba"},
        ],
        response_format={"type": "json_object"},
    )

    config = capturado["config"]
    assert config is not None
    assert config.response_mime_type == "application/json"
    assert resp.choices[0].message.content == '{"sentiment": "neutral"}'


def test_gemini_client_sin_response_format_no_forza_json(monkeypatch):
    """Sin response_format, no se fuerza JSON (config None)."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

    client = GeminiClient()
    capturado = {}

    class FakeResponse:
        text = "texto libre"

    def fake_generate_content(**kwargs):
        capturado.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(client._client.models, "generate_content", fake_generate_content)

    client._create(
        messages=[
            {"role": "system", "content": "Algo."},
            {"role": "user", "content": "otra cosa"},
        ],
    )

    assert capturado["config"] is None


def test_fallback_reintenta_429_y_luego_ok(monkeypatch):
    """Un 429 transitorio se reintenta antes de caer al respaldo."""
    import src.utils.llm_client as llm_mod

    monkeypatch.setattr(llm_mod, "_MAX_RETRIES", 2)
    monkeypatch.setattr(llm_mod, "_RETRY_BASE_DELAY", 0.0)

    llamadas = {"n": 0}

    class Flaky:
        class chat:
            class completions:
                @staticmethod
                def create(model=None, messages=None, response_format=None):
                    llamadas["n"] += 1
                    if llamadas["n"] == 1:
                        raise RuntimeError("429 RESOURCE_EXHAUSTED")
                    return _Respuesta({"ok": True})

    class NoCaer:
        # Si se usa el respaldo, el test falla.
        class chat:
            class completions:
                @staticmethod
                def create(model=None, messages=None, response_format=None):
                    raise AssertionError("no debería caer al respaldo")

    client = FallbackLLMClient(Flaky(), NoCaer())
    resp = client.chat.completions.create(messages=[])
    assert resp.choices[0].message.content == '{"ok": true}'
    assert llamadas["n"] == 2  # 1 fallo transitorio + 1 éxito


def test_fallback_cae_al_respaldo_si_429_persiste(monkeypatch):
    """Un 429 persistente cae al respaldo tras agotar los reintentos."""
    import src.utils.llm_client as llm_mod
    from src.utils.rule_based import RuleBasedClient

    monkeypatch.setattr(llm_mod, "_MAX_RETRIES", 1)
    monkeypatch.setattr(llm_mod, "_RETRY_BASE_DELAY", 0.0)

    class Siempre429:
        class chat:
            class completions:
                @staticmethod
                def create(model=None, messages=None, response_format=None):
                    raise RuntimeError("429 RESOURCE_EXHAUSTED")

    client = FallbackLLMClient(Siempre429(), RuleBasedClient())
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de sentimiento."},
            {"role": "user", "content": "Analiza el sentimiento:\n\nNo me funciona"},
        ],
    )
    import json
    sent = json.loads(resp.choices[0].message.content)
    assert sent["sentiment"] == "negativo"  # cayó a rule_based
