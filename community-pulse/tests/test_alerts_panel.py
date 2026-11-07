"""Tests del panel de alertas (lógica pura, sin runtime de Streamlit).

El componente separa build_alert_items() (testeable en CI) de la capa
render_alerts() (solo Streamlit). Estos tests cubren la lógica pura.
"""

from unittest.mock import Mock

from src.interface.components.alerts_panel import (
    build_alerta,
    build_alert_items,
    _pct,
)
from src.decisions.engine import DecisionEngine


# ----------------------------------------------------------------------
# build_alert_items: métricas y tolerancia
# ----------------------------------------------------------------------
def test_metricas_desde_resumen_ejecutivo():
    decisiones = {
        "resumen_ejecutivo": {
            "miembros_en_riesgo": 2,
            "dudas_detectadas": 1,
            "testimonios_destacables": 1,
            "acciones_automaticas": 4,
        },
        "acciones_recomendadas": [],
    }
    modelo = build_alert_items(decisiones)
    assert modelo["metricas"]["miembros_en_riesgo"] == 2
    assert modelo["metricas"]["dudas_detectadas"] == 1
    assert modelo["metricas"]["testimonios_destacables"] == 1
    assert modelo["metricas"]["acciones_automaticas"] == 4
    assert modelo["alertas"] == []


def test_tolerancia_decisiones_vacias():
    """El panel no explota con decisiones vacías o sin estructura."""
    for decisiones in ({}, None, {"acciones_recomendadas": []}):
        modelo = build_alert_items(decisiones)
        assert modelo["metricas"]["miembros_en_riesgo"] == 0
        assert modelo["metricas"]["acciones_automaticas"] == 0
        assert modelo["alertas"] == []


# ----------------------------------------------------------------------
# build_alerta: formato por tipo de acción
# ----------------------------------------------------------------------
def test_alerta_miembro_muestra_porcentaje():
    alerta = build_alerta({
        "tipo": "alerta_miembro",
        "autor": "João",
        "razon": "Frustración técnica",
        "nivel_riesgo": 0.82,
        "accion_sugerida": "contactar_individualmente",
    })
    assert alerta["nivel"] == "error"
    assert "João" in alerta["titulo"]
    assert "Nivel de riesgo: 82%" in alerta["lineas"]
    assert any("contactar_individualmente" in l for l in alerta["lineas"])


def test_derivar_mentoria_bloque():
    alerta = build_alerta({
        "tipo": "derivar_mentoria",
        "tema": "langgraph",
        "veces_detectada": 3,
        "mentor_sugerido": "especialista_langgraph",
    })
    assert alerta["nivel"] == "warning"
    assert any("langgraph" in l for l in alerta["lineas"])
    assert any("especialista_langgraph" in l for l in alerta["lineas"])


def test_publicar_prioritario_bloque():
    alerta = build_alerta({
        "tipo": "publicar_prioritario",
        "razon": "Testimonio con relevancia 0.92",
        "prioridad": "ALTA",
        "activo_sugerido": "post_linkedin",
    })
    assert alerta["nivel"] == "success"
    assert any("ALTA" in l for l in alerta["lineas"])
    assert any("post_linkedin" in l for l in alerta["lineas"])


def test_generar_faq_bloque():
    alerta = build_alerta({
        "tipo": "generar_faq",
        "razon": "Duda técnica identificada",
        "activo_sugerido": "faq_tip",
    })
    assert alerta["nivel"] == "info"
    assert "FAQ" in alerta["titulo"]


def test_fallback_generico_para_tipos_futuros():
    """Tipos de acción no conocidos no rompen el panel."""
    alerta = build_alerta({"tipo": "escalar_producto", "razon": "Queja de curso"})
    assert alerta["nivel"] == "info"
    assert "escalar_producto" in alerta["titulo"]
    assert "Queja de curso" in alerta["lineas"]


# ----------------------------------------------------------------------
# _pct
# ----------------------------------------------------------------------
def test_pct_formatea_numeros_y_guion():
    assert _pct(0.82) == "82%"
    assert _pct(1) == "100%"
    assert _pct("alto") == "-"
    assert _pct(None) == "-"


# ----------------------------------------------------------------------
# Integración: DecisionEngine → build_alert_items
# ----------------------------------------------------------------------
def test_integracion_engine_a_panel():
    """Las decisiones reales del engine se renderizan como alertas."""
    engine = DecisionEngine(
        llm_client=Mock(),
        historial={
            "dudas_resueltas": [],
            "miembros_tracking": {"João": {"sentimiento_promedio": 0.7}},
        },
    )
    batch = {
        "mensajes_analizados": [
            {
                "id": "1",
                "autor": "Mariana",
                "categoria_sugerida": "caso_exito",
                "relevancia": 0.92,
                "sentimiento": {"score": 0.95},
            },
            {
                "id": "2",
                "autor": "João",
                "texto": "No me funciona el bucket, error tras error, me rindo",
                "sentimiento": {"etiqueta": "negativo", "score": 0.1},
            },
        ]
    }
    decisiones = engine.process_batch(batch)
    modelo = build_alert_items(decisiones)

    niveles = [a["nivel"] for a in modelo["alertas"]]
    assert "error" in niveles        # alerta miembro João
    assert "success" in niveles      # testimonio prioritario Mariana

    alerta_joao = next(a for a in modelo["alertas"] if a["nivel"] == "error")
    assert "João" in alerta_joao["titulo"]
    assert "%" in alerta_joao["lineas"][1]

    assert modelo["metricas"]["testimonios_destacables"] == 1
    assert modelo["metricas"]["miembros_en_riesgo"] >= 1