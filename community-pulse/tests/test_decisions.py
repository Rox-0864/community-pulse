"""Tests del módulo de decisiones (spec: modulo_toma_decisiones.md).

Los 6 tests del spec + 2 de regresión:
- test_engine_tolerates_orchestrator_nested_format: el engine debe leer
  el formato ANIDADO que produce full_analysis() del orchestrator
  (relevancia_marketing vs relevancia plana).
- test_build_notifications_member_alert_includes_senales: la notificación
  de alerta_miembro requiere senales en la acción (bug detectado al
  implementar build_notifications).
"""

from unittest.mock import Mock

from src.decisions.engine import DecisionEngine
from src.decisions.member_risk import MemberRiskDetector
from src.decisions.recurring_topics import RecurringTopicsDetector
from src.decisions.escalation import EscalationRules


# ----------------------------------------------------------------------
# Tests del spec (formato plano)
# ----------------------------------------------------------------------
def test_testimonio_prioritario():
    """R1: testimonio con relevancia alta → publicar prioritario."""
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "1",
            "autor": "Mariana",
            "categoria_sugerida": "caso_exito",
            "relevancia": 0.92,
            "sentimiento": {"score": 0.95},
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "publicar_prioritario" for a in acciones)


def test_duda_tecnica_genera_faq():
    """R2: categoría faq_tip → generar FAQ."""
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "2",
            "autor": "Lucas",
            "categoria_sugerida": "faq_tip",
            "temas": ["langgraph"],
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "generar_faq" for a in acciones)


def test_sentimiento_negativo_alerta():
    """R3: sentimiento negativo → alerta puntual."""
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "3",
            "autor": "João",
            "sentimiento": {"etiqueta": "negativo", "score": 0.2},
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "alerta_sentimiento_puntual" for a in acciones)


def test_member_risk_detection():
    """S1+S2+S3: caída emocional + frustración → riesgo > 0.6."""
    detector = MemberRiskDetector(llm_client=Mock(), historial={
        "miembros_tracking": {
            "João": {"sentimiento_promedio": 0.7}
        }
    })
    mensajes = [
        {"texto": "No me funciona nada", "sentimiento": {"score": 0.2}},
        {"texto": "error tras error en OCI, me rindo", "sentimiento": {"score": 0.1}},
    ]
    resultado = detector.evaluate_author("João", mensajes)
    assert resultado["nivel_riesgo"] > 0.6
    # "frustraci" es la raíz común de "frustracion"/"frustración"
    # (el spec tiene un bug de acentos: test busca sin tilde, código con tilde)
    assert "frustraci" in resultado["razon"].lower()
    assert resultado["accion_sugerida"] == "contactar_individualmente"


def test_recurring_topics():
    """Duda 3+ veces (historial + lote) → derivar a mentoría."""
    detector = RecurringTopicsDetector(umbral=3)
    historial = [
        {"tema": "langgraph", "veces": 2},
        {"tema": "OCI", "veces": 1},
    ]
    mensajes = [
        {"temas": ["langgraph"], "categoria_sugerida": "faq_tip"},
        {"temas": ["langgraph"], "categoria_sugerida": "faq_tip"},
    ]
    resultado = detector.detect(mensajes, historial)
    assert any(d["tema"] == "langgraph" for d in resultado)
    assert resultado[0]["mentor_sugerido"] == "especialista_langgraph"
    assert not any(d["tema"] == "oci" for d in resultado)  # solo 1 vez < umbral


def test_escalation_classification():
    """Clasifica gravedad por nivel de riesgo."""
    reglas = EscalationRules()

    critico = reglas.classify({"nivel_riesgo": 0.9})
    assert critico["nivel"] == "CRITICO"

    alto = reglas.classify({"nivel_riesgo": 0.7})
    assert alto["nivel"] == "ALTO"

    medio = reglas.classify({"nivel_riesgo": 0.5})
    assert medio["nivel"] == "MEDIO"

    info = reglas.classify({"nivel_riesgo": 0.1})
    assert info["nivel"] == "INFO"


# ----------------------------------------------------------------------
# Tests de regresión (descubrimientos de implementación)
# ----------------------------------------------------------------------
def test_engine_tolerates_orchestrator_nested_format():
    """
    El engine lee el formato ANIDADO que produce full_analysis():
    relevancia_marketing.score en lugar de relevancia plano.
    """
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "4",
            "autor": "Ana",
            "texto": "Conseguí trabajo como dev en Oracle",
            "canal": "discord",
            "analisis": {
                "sentimiento": {"etiqueta": "muy_positivo", "score": 0.95},
                "temas": ["contratacion_logro", "testimonio"],
                "relevancia_marketing": {"score": 0.9},
                "categoria_sugerida": "caso_exito",
            },
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "publicar_prioritario" for a in acciones)


def test_build_notifications_member_alert_includes_senales():
    """
    Regresión: build_member_alert requiere senales en la acción.
    La acción alerta_miembro debe cargar las senales del detector,
    si no → KeyError al construir la notificación.
    """
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "5",
            "autor": "João",
            "texto": "no me funciona el bucket, error tras error, me rindo",
            "sentimiento": {"etiqueta": "negativo", "score": 0.1},
        }]
    }
    decisiones = engine.process_batch(batch)
    notificaciones = engine.build_notifications(decisiones)
    assert any(
        n["tipo_notificacion"] == "ALERTA_MIEMBRO" for n in notificaciones
    )


def test_recurring_tech_derived_from_text():
    """
    La misma duda técnica sobre UNA tecnología suma recurrencia aunque
    el análisis solo produzca el tema genérico "duda_tecnica".

    Regresión: el categorizador no emite "langgraph" como tema, así que
    el detector deriva la tecnología del texto para acumular contra
    el historial (spec: misma duda 3+ veces → mentoría).
    """
    detector = RecurringTopicsDetector(umbral=3)
    historial = [{"tema": "langgraph", "veces": 2}]
    mensajes = [{
        "categoria_sugerida": "faq_tip",
        "temas": ["duda_tecnica"],
        "texto": "Tengo dudas sobre los nodos condicionales en LangGraph",
    }]
    resultado = detector.detect(mensajes, historial)
    assert any(d["tema"] == "langgraph" and d["veces_detectada"] == 3
               for d in resultado)


def test_engine_alerta_miembro_en_umbral_exacto():
    """
    Miembro con riesgo EXACTAMENTE en el umbral (0.60) debe generar
    alerta_miembro. Regresión: el engine usaba ">" estricto y silenciaba
    el límite, mientras el detector ya decidía "contactar_individualmente"
    con ">=" (inconsistencia de umbral).

    João sin historial: sentimiento 0.30 + caída 0.20 (default 0.5) +
    frustración ("error", "trabado") → (0.70*0.4) + (0.20*0.35) + 0.25 = 0.60
    """
    engine = DecisionEngine(llm_client=Mock())
    lote = {
        "mensajes_analizados": [{
            "id": "msg_joao",
            "autor": "João Pereira",
            "texto": "No me funciona el bucket, error tras error. Estoy trabado.",
            "categoria_sugerida": "alerta_sentimiento",
            "sentimiento": {"etiqueta": "negativo", "score": 0.30},
        }]
    }
    decisiones = engine.process_batch(lote)
    alertas = [a for a in decisiones["acciones_recomendadas"]
               if a["tipo"] == "alerta_miembro"]
    assert alertas, "riesgo 0.60 == umbral debe alertar"
    assert alertas[0]["nivel_riesgo"] == 0.6
    assert alertas[0]["accion_sugerida"] == "contactar_individualmente"


def test_duda_tecnica_negativa_genera_faq_y_alerta():
    """
    Regresión: un miembro frustrado que pide ayuda técnica debe generar
    TANTO el FAQ (contenido) COMO la alerta de sentimiento (riesgo).

    Antes la regla `faq_tip` cortaba la ejecución y se perdía la alerta
    de sentimiento para quien pide ayuda con frustración.
    """
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "8",
            "autor": "João",
            "categoria_sugerida": "faq_tip",
            "temas": ["oci"],
            "sentimiento": {"etiqueta": "negativo", "score": 0.2},
        }]
    }
    resultado = engine.process_batch(batch)
    tipos = {a["tipo"] for a in resultado["acciones_recomendadas"]}
    assert "generar_faq" in tipos
    assert "alerta_sentimiento_puntual" in tipos


def test_resumen_ejecutivo():
    """El resumen cuenta las acciones por tipo."""
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [
            {
                "id": "6",
                "autor": "Mariana",
                "categoria_sugerida": "caso_exito",
                "relevancia": 0.92,
                "sentimiento": {"score": 0.95},
            },
            {
                "id": "7",
                "autor": "Lucas",
                "categoria_sugerida": "faq_tip",
                "temas": ["docker"],
                "sentimiento": {"score": 0.5},
            },
        ]
    }
    resultado = engine.process_batch(batch)
    resumen = resultado["resumen_ejecutivo"]
    assert resumen["testimonios_destacables"] == 1
    assert resumen["dudas_detectadas"] == 1
    assert resumen["acciones_automaticas"] == 2