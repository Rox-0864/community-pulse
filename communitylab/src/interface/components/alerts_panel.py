"""
CommunityLab — Panel de alertas y decisiones (Dashboard).

Componente container/presentational:
- build_alert_items(): lógica PURA, sin Streamlit → testeable en CI.
  Convierte las decisiones del engine en métricas + bloques de alerta.
- render_alerts(): capa de presentación delgada que pinta el resultado.

Formato de entrada (producido por DecisionEngine.process_batch):
{
  "resumen_ejecutivo": {"miembros_en_riesgo": int, "dudas_detectadas": int,
                        "testimonios_destacables": int, "acciones_automaticas": int},
  "acciones_recomendadas": [
      {"tipo": "alerta_miembro" | "derivar_mentoria" | "publicar_prioritario" |
               "generar_faq" | "alerta_sentimiento_puntual", ...}
  ]
}

Responsable: Software Engineer
"""

import streamlit as st


# ----------------------------------------------------------------------
# Lógica pura (testeable sin Streamlit)
# ----------------------------------------------------------------------
def build_alert_items(decisiones: dict) -> dict:
    """
    Transforma las decisiones del engine en un modelo de UI.

    Returns:
        {
          "metricas": {miembros_en_riesgo, dudas_detectadas,
                       testimonios_destacables, acciones_automaticas},
          "alertas": [{nivel, titulo, lineas}, ...]
        }
        nivel ∈ {error, warning, success, info} (mapping de st.*)
    """
    resumen = decisiones.get("resumen_ejecutivo", {}) if decisiones else {}
    metricas = {
        "miembros_en_riesgo": resumen.get("miembros_en_riesgo", 0),
        "dudas_detectadas": resumen.get("dudas_detectadas", 0),
        "testimonios_destacables": resumen.get("testimonios_destacables", 0),
        "acciones_automaticas": resumen.get("acciones_automaticas", 0),
    }

    acciones = decisiones.get("acciones_recomendadas", []) if decisiones else []
    alertas = [build_alerta(a) for a in acciones]

    return {"metricas": metricas, "alertas": alertas}


def build_alerta(accion: dict) -> dict:
    """Convierte UNA acción del engine en un bloque de alerta de UI."""
    tipo = accion.get("tipo", "desconocida")
    razon = accion.get("razon", "")

    if tipo == "alerta_miembro":
        return {
            "nivel": "error",
            "titulo": f"⚠️ ALERTA — {accion.get('autor', 'miembro')}",
            "lineas": [
                razon,
                f"Nivel de riesgo: {_pct(accion.get('nivel_riesgo'))}",
                f"Acción sugerida: {accion.get('accion_sugerida', '-')}",
            ],
        }

    if tipo == "derivar_mentoria":
        return {
            "nivel": "warning",
            "titulo": "📚 DERIVACIÓN A MENTORÍA",
            "lineas": [
                f"Tema: {accion.get('tema', '-')}",
                f"Veces detectada: {accion.get('veces_detectada', 0)}",
                f"Mentor sugerido: {accion.get('mentor_sugerido', '-')}",
            ],
        }

    if tipo == "publicar_prioritario":
        return {
            "nivel": "success",
            "titulo": "🚀 PUBLICAR PRIORITARIO",
            "lineas": [
                razon,
                f"Prioridad: {accion.get('prioridad', '-')}",
                f"Activo sugerido: {accion.get('activo_sugerido', '-')}",
            ],
        }

    if tipo == "generar_faq":
        return {
            "nivel": "info",
            "titulo": "📝 FAQ GENERADO",
            "lineas": [razon, f"Activo: {accion.get('activo_sugerido', 'faq_tip')}"],
        }

    if tipo == "alerta_sentimiento_puntual":
        return {
            "nivel": "warning",
            "titulo": "⚠️ SENTIMIENTO NEGATIVO",
            "lineas": [razon],
        }

    # Fallback genérico para tipos futuros
    lineas = [razon] if razon else []
    extra = {k: v for k, v in accion.items() if k not in ("tipo", "razon") and v}
    if extra:
        lineas.extend(f"{k}: {v}" for k, v in extra.items())
    return {"nivel": "info", "titulo": f"📌 Acción: {tipo}", "lineas": lineas}


def _pct(valor) -> str:
    """Formatea un 0-1 como porcentaje. Devuelve '-' si no es numérico."""
    if isinstance(valor, (int, float)):
        return f"{valor:.0%}"
    return "-"


# ----------------------------------------------------------------------
# Capa de presentación (Streamlit)
# ----------------------------------------------------------------------
def render_alerts(decisiones: dict):
    """Renderiza el panel de decisiones en el dashboard."""
    st.subheader("🚨 Decisiones Automáticas")

    modelo = build_alert_items(decisiones)
    metricas = modelo["metricas"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Miembros en riesgo", metricas["miembros_en_riesgo"])
    col2.metric("Dudas detectadas", metricas["dudas_detectadas"])
    col3.metric("Testimonios destacables", metricas["testimonios_destacables"])
    col4.metric("Acciones automáticas", metricas["acciones_automaticas"])

    st.markdown("---")

    # Mapear nivel → función de render de Streamlit
    renderers = {
        "error": st.error,
        "warning": st.warning,
        "success": st.success,
        "info": st.info,
    }

    for alerta in modelo["alertas"]:
        renderer = renderers.get(alerta["nivel"], st.info)
        renderer(_format_alerta(alerta))

    if not modelo["alertas"] and not any(metricas.values()):
        st.info("Sin decisiones que mostrar. Procesá un lote de interacciones arriba.")


def _format_alerta(alerta: dict) -> str:
    """Arma el markdown de un bloque de alerta."""
    titulo = f"**{alerta['titulo']}**"
    cuerpo = "\n\n".join(f"• {linea}" for linea in alerta["lineas"] if linea)
    return f"{titulo}\n\n{cuerpo}" if cuerpo else titulo