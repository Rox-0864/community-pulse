"""
Community Pulse — Orquestador del análisis completo de un mensaje.

Pipeline: Sentimiento → Categorización → Relevancia → Categoría sugerida.
Responsable: Data Scientists
"""

from src.analysis.sentiment import analyze_sentiment
from src.analysis.categorization import categorize_message
from src.analysis.relevance import score_relevance


def full_analysis(message: dict, llm_client) -> dict:
    """Ejecuta el análisis completo de un mensaje."""
    text = message.get("texto", "")
    if not text:
        raise ValueError("Mensaje sin texto para analizar")

    sentimiento = analyze_sentiment(text, llm_client)
    categorias = categorize_message(text, message.get("canal", ""), llm_client)
    relevancia = score_relevance(
        text,
        {"sentimiento": sentimiento, "categorias": categorias},
        llm_client,
    )

    return {
        "id": message.get("id"),
        "autor": message.get("autor"),
        "texto": text,
        "canal": message.get("canal"),
        "analisis": {
            "sentimiento": sentimiento,
            "temas": categorias,
            "relevancia_marketing": relevancia,
            "categoria_sugerida": _sugerir_categoria(sentimiento, categorias, relevancia),
        },
    }


def _sugerir_categoria(sentimiento: dict, categorias: list, relevancia: dict) -> str:
    """Sugiere qué tipo de activo generar basándose en el análisis.

    Prioridad: la duda técnica gana sobre el sentimiento (positivo o negativo)
    porque representa una pregunta concreta que responder como FAQ; el riesgo
    de sentimiento se maneja por separado en el motor de decisiones.

    Robustez: usa ``.get()`` con defaults para degradar con gracia si el LLM
    devuelve un JSON malformado (sin ``etiqueta``, ``score`` o ``categorias``).
    """
    etiqueta = (sentimiento or {}).get("etiqueta", "neutral")
    categorias = categorias or []
    score = (relevancia or {}).get("score", 0.0)

    if "duda_tecnica" in categorias:
        return "faq_tip"
    if etiqueta in ["muy_positivo", "positivo"] and score > 0.8:
        return "caso_exito"
    if etiqueta in ["negativo", "muy_negativo"]:
        return "alerta_sentimiento"
    return "newsletter_highlight"
