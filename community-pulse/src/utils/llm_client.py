"""
Community Pulse — Cliente LLM unificado (Gemini/OpenAI/reglas).

Modos de ejecución:
1. COMMUNITYLAB_LLM_BACKEND=rule_based → RuleBasedClient (offline, sin API keys)
   Ideal para demos, tests y CI. Resuelve sentimiento/categorías/relevancia
   con reglas deterministas en español.
2. GEMINI_API_KEY → GeminiClient (SDK `google.genai`) con respaldo offline
3. OPENAI_API_KEY → OpenAI con respaldo offline

El modelo de Gemini se elige con GEMINI_MODEL. Default: ``gemini-3.5-flash-lite``
(gratis en Google AI Studio). Para Gemma 4 open-weight: ``gemma-4-31b-it``.

Regla de respaldo: si el LLM real falla en runtime (sin internet, API caída,
key inválida), el sistema cae automáticamente a RuleBasedClient y sigue
funcionando offline. Lo mismo si no hay ninguna key configurada.

Responsable: Software Engineer
"""

import os
import re

from dotenv import load_dotenv

# Carga el archivo .env del proyecto (si existe) antes de leer las variables.
load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"

try:
    from google import genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.utils.logger import setup_logger

logger = setup_logger("community-pulse.llm")


def create_llm_client():
    """
    Crea el cliente LLM según las variables de entorno.

    Prioridad: rule_based (explícito) → Gemini → OpenAI → rule_based (respaldo).

    Los clientes reales (Gemini/OpenAI) se envuelven en un FallbackLLMClient
    que, ante un fallo en runtime (sin internet, API no disponible), delega en
    RuleBasedClient para no detener el pipeline.
    """
    # 1. Backend offline explícito (demo/tests/CI): sin intentar LLM real.
    if os.getenv("COMMUNITYLAB_LLM_BACKEND", "").lower() == "rule_based":
        from src.utils.rule_based import RuleBasedClient
        return RuleBasedClient()

    from src.utils.rule_based import RuleBasedClient
    fallback = RuleBasedClient()

    # 2. Gemini con respaldo offline.
    if os.getenv("GEMINI_API_KEY"):
        if genai is None:
            raise ImportError("Instala google-genai: pip install google-genai")
        return FallbackLLMClient(GeminiClient(), fallback)

    # 3. OpenAI con respaldo offline.
    if os.getenv("OPENAI_API_KEY"):
        if OpenAI is None:
            raise ImportError("Instala openai: pip install openai")
        return FallbackLLMClient(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), fallback)

    # 4. Sin key configurada: se opera offline.
    logger.warning("Sin GEMINI_API_KEY ni OPENAI_API_KEY: usando respaldo rule_based.")
    return fallback


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
        response = self._client.models.generate_content(
            model=model_id,
            contents=full_prompt,
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


class FallbackLLMClient:
    """Intenta el cliente principal; ante fallo, delega en el respaldo offline.

    Permite que rule_based sea el respaldo automático cuando no hay internet,
    la API del LLM no responde, o la key es inválida. Expone la misma interfaz
    ``chat.completions.create`` que los demás clientes.
    """

    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self.chat = _FallbackChat(self)

    def _create(self, model=None, messages=None, response_format=None):
        try:
            return self._primary.chat.completions.create(model, messages, response_format)
        except Exception as exc:  # sin internet, API caída, key inválida, etc.
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
