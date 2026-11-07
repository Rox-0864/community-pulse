"""
Community Pulse — Análisis de sentimiento con LLM.

Responsable: Data Scientist 1
"""

import json

from src.prompts.sentiment_prompts import SENTIMENT_SYSTEM_PROMPT
from src.prompts.templates import build_prompt


def analyze_sentiment(text: str, llm_client) -> dict:
    """
    Analiza el sentimiento de un texto usando un LLM.

    Args:
        text: El mensaje de la comunidad
        llm_client: Cliente del LLM (Gemini/OpenAI/Claude)

    Returns:
        dict con etiqueta, score y confianza
    """
    messages = build_prompt(
        SENTIMENT_SYSTEM_PROMPT,
        f"Analiza el sentimiento de este mensaje:\n\n{text}",
    )

    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",  # o el modelo elegido
        messages=messages,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "etiqueta": result.get("sentiment", "neutral"),
        "score": float(result.get("score", 0.5)),
        "confianza": float(result.get("confidence", 0.7)),
        "emocion": result.get("emotion_detected", "neutral"),
        "keywords": result.get("keywords", []),
    }
