"""
Community Pulse — Cliente LLM unificado (Gemini/Groq/OpenAI/reglas).

Modos de ejecución:
1. COMMUNITYLAB_LLM_BACKEND=rule_based → RuleBasedClient (offline, sin API keys)
   Ideal para demos, tests y CI. Resuelve sentimiento/categorías/relevancia
   con reglas deterministas en español.
2. GEMINI_API_KEY → GeminiClient (SDK `google.genai`)
3. GROQ_API_KEY → GroqClient (API OpenAI-compatible, gratuito y rápido)
4. OPENAI_API_KEY → OpenAI

Los proveedores reales se encadenan en orden Gemini → Groq → OpenAI; si uno
falla en runtime (sin internet, API caída, key inválida o cuota agotada), se
delega en el siguiente y al final en RuleBasedClient (offline).

El modelo de Gemini se elige con GEMINI_MODEL (default: ``gemini-3.5-flash-lite``,
gratis en Google AI Studio). El de Groq con GROQ_MODEL (default:
``openai/gpt-oss-120b``).

Responsable: Software Engineer
"""

import os
import re
import time

from dotenv import load_dotenv

# Carga el archivo .env del proyecto (si existe) antes de leer las variables.
load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

# Groq (gratuito, API OpenAI-compatible, alta velocidad). Modelo default:
# ``openai/gpt-oss-120b`` (production, reasoning). Alternativas gratuitas:
# ``openai/gpt-oss-20b`` y ``qwen/qwen3.8-27b``.
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.utils.logger import setup_logger

logger = setup_logger("community-pulse.llm")


def create_llm_client():
    """
    Crea el cliente LLM según las variables de entorno.

    Prioridad: rule_based (explícito) → Gemini → Groq → OpenAI → rule_based.

    Los clientes reales se encadenan con FallbackLLMClient: si el primario
    falla en runtime (sin internet, API caída, key inválida, cuota agotada),
    delega en el siguiente proveedor y al final en RuleBasedClient (offline)
    para no detener el pipeline.
    """
    # 1. Backend offline explícito (demo/tests/CI): sin intentar LLM real.
    if os.getenv("COMMUNITYLAB_LLM_BACKEND", "").lower() == "rule_based":
        from src.utils.rule_based import RuleBasedClient
        return RuleBasedClient()

    from src.utils.rule_based import RuleBasedClient
    rule_based = RuleBasedClient()

    # 2. Proveedores reales disponibles, en orden de preferencia.
    providers = []
    if os.getenv("GEMINI_API_KEY"):
        if genai is None:
            raise ImportError("Instala google-genai: pip install google-genai")
        providers.append(GeminiClient())
    if os.getenv("GROQ_API_KEY"):
        providers.append(GroqClient())

    # 3. OpenAI como camino separado (solo si no hay Gemini ni Groq).
    if not providers and os.getenv("OPENAI_API_KEY"):
        if OpenAI is None:
            raise ImportError("Instala openai: pip install openai")
        return FallbackLLMClient(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), rule_based)

    # 4. Sin ninguna key configurada: se opera offline.
    if not providers:
        logger.warning(
            "Sin GEMINI_API_KEY, GROQ_API_KEY ni OPENAI_API_KEY: usando respaldo rule_based."
        )
        return rule_based

    # 5. Encadenar: primary → siguiente → ... → rule_based.
    client = rule_based
    for provider in reversed(providers):
        client = FallbackLLMClient(provider, client)
    return client


def _clean_json_text(text: str) -> str:
    """Quita fences markdown (```json ... ```) si el modelo los devuelve."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text, count=1)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


class _LLMResponse:
    """Envuelve texto en la forma OpenAI-compatible {choices:[{message:{content}}]}.

    Implementa __await__ para que ``await create(...)`` (generadores) devuelva
    el mismo objeto, además del uso síncrono (módulos de análisis), igual que
    RuleBasedResponse.
    """

    def __init__(self, content: str):
        class _Message:
            def __init__(self, content):
                self.content = content

        class _Choice:
            def __init__(self, content):
                self.message = _Message(content)

        self.choices = [_Choice(content)]

    def __await__(self):
        async def _wrap():
            return self
        return _wrap().__await__()


class GeminiClient:
    """Wrapper para Gemini (SDK google.genai) con interfaz OpenAI-compatible."""

    def __init__(self, model: str = None):
        if genai is None:
            raise ImportError("Instala google-genai: pip install google-genai")
        self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.chat = _GeminiChat(self)

    def _create(self, model: str = None, messages: list = None, response_format: dict = None):
        """Ejecuta una llamada al modelo Gemini y retorna una respuesta compatible."""
        messages = messages or []
        system_prompt = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        user_prompt = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}".strip()

        model_id = model or self.model

        # Forzar JSON limpio (sin fences markdown) cuando el caller pide
        # json_object: el SDK devuelve el JSON directo, sin wrappers de texto.
        config = None
        if (
            response_format
            and response_format.get("type") == "json_object"
            and genai_types is not None
        ):
            config = genai_types.GenerateContentConfig(
                response_mime_type="application/json"
            )

        response = self._client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config=config,
        )
        return _LLMResponse(_clean_json_text(response.text))


class _GeminiChat:
    def __init__(self, owner: "GeminiClient"):
        self.completions = _GeminiCompletions(owner)


class _GeminiCompletions:
    def __init__(self, owner: "GeminiClient"):
        self._owner = owner

    def create(self, model=None, messages=None, response_format=None):
        return self._owner._create(model, messages, response_format)


class GroqClient:
    """Wrapper para Groq (API OpenAI-compatible) con interfaz del pipeline.

    Reutiliza el SDK ``openai`` apuntando a la URL base de Groq. Igual que
    GeminiClient, devuelve una respuesta auto-awaitable para soportar el uso
    síncrono (análisis) y asíncrono (generadores) sin tocar a los callers.
    """

    def __init__(self, model: str = None):
        if OpenAI is None:
            raise ImportError("Instala openai: pip install openai")
        self._client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=os.getenv("GROQ_API_KEY"),
        )
        self.model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.chat = _GroqChat(self)

    def _create(self, model: str = None, messages: list = None, response_format: dict = None):
        messages = messages or []
        model_id = model or self.model
        response = self._client.chat.completions.create(
            model=model_id,
            messages=messages,
            response_format=response_format,
        )
        return _LLMResponse(_clean_json_text(response.choices[0].message.content))


class _GroqChat:
    def __init__(self, owner: "GroqClient"):
        self.completions = _GroqCompletions(owner)


class _GroqCompletions:
    def __init__(self, owner: "GroqClient"):
        self._owner = owner

    def create(self, model=None, messages=None, response_format=None):
        return self._owner._create(model, messages, response_format)


# Errores transitorios (reintentables): cuota agotada (429) o sobrecarga (503).
# Se reintenta con backoff antes de delegar al respaldo.
_RETRYABLE_MARKERS = (
    "429", "503", "resource_exhausted", "unavailable",
    "rate limit", "too many", "overloaded",
)
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0  # segundos; se duplica por intento


def _es_error_transitorio(exc: Exception) -> bool:
    """Detecta si un error es transitorio (429/503) y vale la pena reintentar."""
    texto = str(exc).lower()
    return any(marca in texto for marca in _RETRYABLE_MARKERS)


def _delay_reintento(intento: int) -> float:
    """Backoff exponencial: 1s, 2s, ..."""
    return _RETRY_BASE_DELAY * (2 ** intento)


class FallbackLLMClient:
    """Intenta el cliente principal; ante fallo, delega en el respaldo offline.

    Antes de delegar, reintenta los errores transitorios (429 cuota / 503
    sobrecarga) con backoff exponencial, respetando el consejo de "reintenta
    más tarde" de las APIs. Permite que rule_based sea el respaldo automático
    cuando no hay internet, la API no responde, o la key es inválida. Expone
    la misma interfaz ``chat.completions.create`` que los demás clientes.
    """

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self.chat = _FallbackChat(self)

    def _create(self, model=None, messages=None, response_format=None):
        for intento in range(_MAX_RETRIES + 1):
            try:
                return self._primary.chat.completions.create(model, messages, response_format)
            except Exception as exc:  # sin internet, API caída, key inválida, etc.
                if intento < _MAX_RETRIES and _es_error_transitorio(exc):
                    delay = _delay_reintento(intento)
                    logger.info(
                        "Error transitorio del LLM principal (%s). "
                        "Reintentando en %.1fs (intento %d/%d)...",
                        type(exc).__name__, delay, intento + 1, _MAX_RETRIES,
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "LLM principal no disponible (%s: %s). Usando respaldo rule_based.",
                    type(exc).__name__, exc,
                )
                return self._fallback.chat.completions.create(model, messages, response_format)


class _FallbackChat:
    def __init__(self, owner: "FallbackLLMClient"):
        self.completions = _FallbackCompletions(owner)


class _FallbackCompletions:
    def __init__(self, owner: "FallbackLLMClient"):
        self._owner = owner

    def create(self, model=None, messages=None, response_format=None):
        return self._owner._create(model, messages, response_format)


# Uso: llm_client = create_llm_client()
