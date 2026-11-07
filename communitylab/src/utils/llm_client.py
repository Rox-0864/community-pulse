"""
Community Pulse — Cliente LLM unificado (Gemini/OpenAI/reglas).

Modos de ejecución:
1. COMMUNITYLAB_LLM_BACKEND=rule_based → RuleBasedClient (offline, sin API keys)
   Ideal para demos, tests y CI. Resuelve sentimiento/categorías/relevancia
   con reglas deterministas en español.
2. GEMINI_API_KEY → GeminiClient
3. OPENAI_API_KEY → OpenAI

⚠️ Agregá a .env.example:
   COMMUNITYLAB_LLM_BACKEND=rule_based

Responsable: Software Engineer
"""

import os

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def create_llm_client():
    """
    Crea el cliente LLM según las variables de entorno.

    Prioridad: rule_based (explicito) → Gemini → OpenAI
    """
    if os.getenv("COMMUNITYLAB_LLM_BACKEND", "").lower() == "rule_based":
        from src.utils.rule_based import RuleBasedClient
        return RuleBasedClient()

    if os.getenv("GEMINI_API_KEY"):
        if genai is None:
            raise ImportError("Instala google-generativeai: pip install google-generativeai")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return GeminiClient()
    elif os.getenv("OPENAI_API_KEY"):
        if OpenAI is None:
            raise ImportError("Instala openai: pip install openai")
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        raise ValueError("Configura GEMINI_API_KEY o OPENAI_API_KEY en .env")


class GeminiClient:
    """Wrapper para Gemini con interfaz compatible con el pipeline."""

    def __init__(self, model: str = None):
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    class chat:
        class completions:
            @staticmethod
            def create(model: str, messages: list, response_format: dict = None):
                """Ejecuta una llamada al modelo Gemini."""
                import json
                import google.generativeai as genai

                # Construir el prompt a partir de los mensajes
                system_prompt = next(
                    (m["content"] for m in messages if m["role"] == "system"), ""
                )
                user_prompt = next(
                    (m["content"] for m in messages if m["role"] == "user"), ""
                )

                full_prompt = f"{system_prompt}\n\n{user_prompt}"

                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                gemini_model = genai.GenerativeModel(model)

                response = gemini_model.generate_content(full_prompt)

                class Message:
                    content = response.text

                class Choice:
                    message = Message()

                class Resp:
                    choices = [Choice()]

                return Resp()


# Uso: llm_client = create_llm_client()
