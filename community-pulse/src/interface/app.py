"""
Community Pulse — Interfaz Streamlit.

Dashboard: procesa un lote de interacciones (offline con RuleBasedClient
o con LLM real según COMMUNITYLAB_LLM_BACKEND) y muestra métricas de la
comunidad + el panel de Decisiones Automáticas (alerts_panel).

Responsable: Software Engineer
"""

import asyncio
import json
from pathlib import Path

import streamlit as st

from src.interface.components.alerts_panel import render_alerts

st.set_page_config(
    page_title="Community Pulse",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar con navegación
st.sidebar.title("🚀 Community Pulse")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navegación",
    ["📊 Dashboard", "✍️ Curaduría", "⚡ Generar", "⚙️ Configuración"],
)

if "activos_pendientes" not in st.session_state:
    st.session_state["activos_pendientes"] = []

if "resultado_pipeline" not in st.session_state:
    st.session_state["resultado_pipeline"] = None

# Historial de ejemplo para el demo: dudas previas de la semana + trayectoria
# de miembros. Con esto el motor detecta: duda LangGraph repetida (mentoría)
# y caída emocional de João (alerta miembro).
_HISTORIAL_DEMO = {
    "dudas_resueltas": [{"tema": "langgraph", "veces": 2}],
    "miembros_tracking": {
        "João Pereira": {"sentimiento_promedio": 0.7},
    },
}


def _correr_pipeline(payload: dict, usar_historial: bool) -> dict:
    """Ejecuta el pipeline completo (async) dentro del script de Streamlit."""
    from src.orchestration.pipeline import CommunityPulsePipeline
    from src.utils.llm_client import create_llm_client
    from src.oci.client import create_oci_storage

    historial = _HISTORIAL_DEMO if usar_historial else None
    pipeline = CommunityPulsePipeline(
        llm_client=create_llm_client(),
        historial=historial,
        oci_storage=create_oci_storage(),
    )
    return asyncio.run(pipeline.process(payload))


def _render_dashboard():
    st.title("📊 Dashboard de la Comunidad")

    col_src, col_hist = st.columns([2, 1])
    with col_src:
        fuente = st.radio(
            "Fuente de datos",
            ["data/sample/messages.json", "Subir archivo JSON"],
            horizontal=True,
        )
    with col_hist:
        usar_historial = st.checkbox(
            "Usar historial de ejemplo (dudas previas + trayectoria)",
            value=True,
            help="Agrega dudas resueltas y sentimiento histórico de miembros "
                 "para que el motor detecte recurrencias y caídas emocionales.",
        )

    payload = None
    if "sample" in fuente:
        sample = Path("data/sample/messages.json")
        if sample.exists():
            payload = json.loads(sample.read_text())
            st.caption(
                f"Sample: {len(payload.get('interacciones', []))} "
                f"interacciones · {payload.get('periodo_referencia', '-')}"
            )
        else:
            st.warning("No se encontró data/sample/messages.json")
    else:
        uploaded = st.file_uploader("Archivo JSON", type=["json"])
        if uploaded is not None:
            payload = json.load(uploaded)
            st.caption(f"Archivo: {len(payload.get('interacciones', []))} interacciones")

    if payload and st.button("🚀 Analizar lote", type="primary"):
        with st.spinner("Procesando pipeline (análisis → decisiones → activos)..."):
            try:
                st.session_state["resultado_pipeline"] = _correr_pipeline(
                    payload, usar_historial
                )
            except Exception as e:  # noqa: BLE001 — Streamlit muestra el error al usuario
                st.error(f"Error procesando el lote: {e}")

    resultado = st.session_state.get("resultado_pipeline")
    if resultado:
        resumen = resultado.get("resumen_comunidad", {})
        activos = resultado.get("activos_distribucion_generados") or {}
        total_activos = sum(len(v) for v in activos.values())

        st.markdown("### 📈 Resumen de la comunidad")
        c1, c2, c3 = st.columns(3)
        c1.metric("Interacciones procesadas", resumen.get("total_interacciones_procesadas", 0))
        c2.metric("Sentimiento predominante", resumen.get("sentimiento_predominante", "-"))
        c3.metric("Activos generados", total_activos)

        st.markdown("---")
        render_alerts(resumen.get("decisiones", {}))

        with st.expander("📦 Activos de distribución generados"):
            st.json(activos)


def _render_curaduria():
    st.title("✍️ Panel de Curaduría")
    pendientes = st.session_state.get("activos_pendientes", [])
    if not pendientes:
        st.info("Los activos generados aparecerán aquí para su aprobación.")
    for activo in pendientes:
        st.json(activo)


if page == "📊 Dashboard":
    _render_dashboard()

elif page == "✍️ Curaduría":
    _render_curaduria()

elif page == "⚡ Generar":
    st.title("⚡ Generar Activos")
    st.markdown("Sube un archivo JSON con interacciones de la comunidad:")

    uploaded = st.file_uploader("Archivo JSON", type=["json"])
    if uploaded is not None:
        data = json.load(uploaded)
        st.success(f"Archivo cargado: {len(data.get('interacciones', []))} interacciones")
        st.json(data)

elif page == "⚙️ Configuración":
    st.title("⚙️ Configuración")
    st.markdown("Verifica tus variables de entorno en `.env`.")
    st.code(
        "COMMUNITYLAB_LLM_BACKEND=rule_based\n"
        "GEMINI_API_KEY=tus-api-key\n"
        "OCI_USER_ID=..., OCI_BUCKET_NAME=...",
        language="bash",
    )
    st.caption(
        "`COMMUNITYLAB_LLM_BACKEND=rule_based` ejecuta el pipeline SIN API keys "
        "(demo/tests). Sin esta variable, se usa Gemini/OpenAI según las keys."
    )