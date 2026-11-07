"""Tests de los módulos de análisis.

Cubre: sentiment.py, categorization.py, relevance.py y orchestrator.py
(espec: analisis de sentimiento, categorización y relevancia del pipeline).
"""

import pytest

from src.analysis.sentiment import analyze_sentiment
from src.analysis.categorization import categorize_message, CATEGORIAS_DISPONIBLES
from src.analysis.relevance import score_relevance
from src.analysis.orchestrator import full_analysis, _sugerir_categoria


# ----------------------------------------------------------------------
# Sentimiento
# ----------------------------------------------------------------------
def test_analyze_sentiment_mapea_campos(fake_llm):
    llm = fake_llm({
        "sentiment": "positivo",
        "score": 0.8,
        "confidence": 0.9,
        "emotion_detected": "alegría",
        "keywords": ["genial", "gracias"],
    })
    result = analyze_sentiment("genial, gracias", llm)

    assert result["etiqueta"] == "positivo"
    assert result["score"] == 0.8
    assert result["confianza"] == 0.9
    assert result["emocion"] == "alegría"
    assert result["keywords"] == ["genial", "gracias"]


def test_analyze_sentiment_defaults(fake_llm):
    """Un payload vacío no rompe el mapeo: aplica los defaults."""
    llm = fake_llm({})
    result = analyze_sentiment("cualquier texto", llm)

    assert result["etiqueta"] == "neutral"
    assert result["score"] == 0.5
    assert result["confianza"] == 0.7
    assert result["emocion"] == "neutral"
    assert result["keywords"] == []


# ----------------------------------------------------------------------
# Categorización
# ----------------------------------------------------------------------
def test_categorias_disponibles_completas():
    assert len(CATEGORIAS_DISPONIBLES) == 7
    for categoria in (
        "contratacion_logro", "duda_tecnica", "feedback_positivo",
        "feedback_negativo", "sugerencia", "testimonio", "general",
    ):
        assert categoria in CATEGORIAS_DISPONIBLES


def test_categorize_message_retorna_lista(fake_llm):
    llm = fake_llm({
        "categorias": ["duda_tecnica", "feedback_negativo"],
        "confianza": 0.8,
    })
    result = categorize_message("no entiendo docker", "discord", llm)

    assert result == ["duda_tecnica", "feedback_negativo"]


def test_categorize_message_sin_categorias_devuelve_lista_vacia(fake_llm):
    llm = fake_llm({})
    result = categorize_message("texto", "discord", llm)

    assert result == []


# ----------------------------------------------------------------------
# Relevancia
# ----------------------------------------------------------------------
def test_score_relevance_usa_promedio_ponderado(fake_llm):
    llm = fake_llm({
        "shareability": 0.9,
        "promedio_ponderado": 0.85,
        "justificacion": "testimonio inspirador",
    })
    result = score_relevance(
        "conseguí trabajo",
        {"sentimiento": {"etiqueta": "positivo"},
         "categorias": ["contratacion_logro"]},
        llm,
    )

    assert result["score"] == 0.85
    assert result["razon"] == "testimonio inspirador"
    assert result["desglose"]["shareability"] == 0.9


def test_score_relevance_fallback_a_score(fake_llm):
    """Sin 'promedio_ponderado', cae al campo 'score'."""
    llm = fake_llm({"score": 0.6})
    result = score_relevance("texto", {}, llm)

    assert result["score"] == 0.6


def test_score_relevance_default(fake_llm):
    llm = fake_llm({})
    result = score_relevance("texto", {}, llm)

    assert result["score"] == 0.5
    assert result["razon"] == ""


# ----------------------------------------------------------------------
# Orquestador
# ----------------------------------------------------------------------
def test_full_analysis_estructura(fake_llm):
    llm = fake_llm([
        {"sentiment": "neutral", "score": 0.5, "confidence": 0.7},
        {"categorias": ["duda_tecnica"]},
        {"promedio_ponderado": 0.45, "justificacion": "duda sin relevancia alta"},
    ])
    result = full_analysis(
        {"id": "m1", "autor": "Ana", "texto": "no entiendo langgraph",
         "canal": "discord"},
        llm,
    )

    # Hace exactamente 3 llamadas al LLM (sentimiento → categorías → relevancia)
    assert len(llm.calls) == 3

    assert result["id"] == "m1"
    assert result["autor"] == "Ana"
    assert result["canal"] == "discord"
    assert result["analisis"]["sentimiento"]["etiqueta"] == "neutral"
    assert result["analisis"]["temas"] == ["duda_tecnica"]
    assert result["analisis"]["relevancia_marketing"]["score"] == 0.45
    assert result["analisis"]["categoria_sugerida"] == "faq_tip"


def test_full_analysis_sin_texto_lanza_error(fake_llm):
    llm = fake_llm({})
    with pytest.raises(ValueError):
        full_analysis({"id": "x", "texto": ""}, llm)


@pytest.mark.parametrize(
    "sentimiento,categorias,score,esperado",
    [
        ({"etiqueta": "muy_positivo"}, [], 0.9, "caso_exito"),
        ({"etiqueta": "positivo"}, [], 0.9, "caso_exito"),
        ({"etiqueta": "neutral"}, ["duda_tecnica"], 0.4, "faq_tip"),
        ({"etiqueta": "negativo"}, [], 0.4, "alerta_sentimiento"),
        ({"etiqueta": "muy_negativo"}, [], 0.4, "alerta_sentimiento"),
        ({"etiqueta": "neutral"}, [], 0.4, "newsletter_highlight"),
    ],
)
def test_sugerir_categoria(sentimiento, categorias, score, esperado):
    relevancia = {"score": score}
    assert _sugerir_categoria(sentimiento, categorias, relevancia) == esperado
