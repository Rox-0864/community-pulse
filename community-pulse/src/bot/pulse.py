"""
Community Pulse — Lógica pura del bot de Discord.

Funciones SIN dependencia de la librería ``discord.py``: convierten mensajes
de Discord al payload del pipeline y formatean el resultado para publicarlo
en un canal. Testeables sin conexión real ni token.

Responsable: Backend Developer
"""

from typing import Optional

DEFAULT_LIMIT = 50
ORIGEN_COMUNIDAD = "discord"
MAX_DISCORD_MESSAGE = 1900  # Discord limita a 2000 chars; dejamos margen


# ----------------------------------------------------------------------
# Extracción de campos (tolera objetos Discord y dicts)
# ----------------------------------------------------------------------
def _autor(m) -> str:
    """Autor del mensaje: objeto ``discord.Message`` o dict."""
    if hasattr(m, "author"):
        author = m.author
        return (
            getattr(author, "name", None)
            or getattr(author, "display_name", None)
            or "Anónimo"
        )
    return m.get("autor", m.get("author", "Anónimo"))


def _canal(m) -> str:
    """Canal del mensaje."""
    if hasattr(m, "channel"):
        return getattr(m.channel, "name", "general")
    return m.get("canal", m.get("channel", "general"))


def _texto(m) -> str:
    """Texto del mensaje."""
    if hasattr(m, "content"):
        return m.content or ""
    return m.get("texto", m.get("content", ""))


def _timestamp(m) -> str:
    """Timestamp ISO del mensaje (o cadena vacía)."""
    if hasattr(m, "created_at"):
        return m.created_at.isoformat() if m.created_at else ""
    return m.get("timestamp", m.get("created_at", ""))


def _es_bot(m) -> bool:
    """True si el mensaje lo escribió un bot (para no realimentar el pipeline)."""
    if hasattr(m, "author"):
        return bool(getattr(m.author, "bot", False))
    return bool(m.get("bot", False))


# ----------------------------------------------------------------------
# Conversión mensajes → payload del pipeline
# ----------------------------------------------------------------------
def build_batch_from_messages(
    messages,
    periodo: str = "Discord_live",
    exclude_bot: bool = True,
    exclude_prefix: str = "!",
) -> dict:
    """
    Convierte mensajes de Discord en el payload que espera el pipeline.

    Acepta objetos tipo ``discord.Message`` (acceso por atributo) o dicts
    (acceso por clave). Descarta:
    - mensajes de bots (si ``exclude_bot``),
    - mensajes vacíos,
    - mensajes que arrancan con ``exclude_prefix`` (comandos del propio bot).

    El resultado es compatible con ``CommunityPulsePipeline.process`` y con
    la ruta ``POST /webhook``.
    """
    interacciones = []
    for m in messages:
        if exclude_bot and _es_bot(m):
            continue
        texto = _texto(m).strip()
        if not texto:
            continue
        if exclude_prefix and texto.startswith(exclude_prefix):
            continue
        interacciones.append(
            {
                "autor": _autor(m),
                "canal": _canal(m),
                "texto": texto,
                "timestamp": _timestamp(m),
            }
        )
    return {
        "origen_comunidad": ORIGEN_COMUNIDAD,
        "periodo_referencia": periodo,
        "interacciones": interacciones,
    }


# ----------------------------------------------------------------------
# Formateo del resultado → mensaje de Discord
# ----------------------------------------------------------------------
def format_pulse_result(result: dict) -> str:
    """
    Formatea el resultado del pipeline en un resumen legible para Discord.

    Agrupa las acciones recomendadas por tipo (alertas de miembros,
    mentorías, testimonios, FAQs) y lista los activos generados.
    """
    if result.get("status") != "exito":
        error = result.get("error") or "error desconocido"
        return f"⚠️ El análisis falló: {error}"

    resumen = result.get("resumen_comunidad", {})
    total = resumen.get("total_interacciones_procesadas", 0)
    sentimiento = resumen.get("sentimiento_predominante", "n/a")
    decisiones = resumen.get("decisiones", {})
    acciones = decisiones.get("acciones_recomendadas", [])

    lineas = [
        "📊 **Community Pulse** — resumen del lote",
        f"Interacciones procesadas: `{total}` · Sentimiento predominante: `{sentimiento}`",
    ]

    alertas = [a for a in acciones if a["tipo"] == "alerta_miembro"]
    mentorias = [a for a in acciones if a["tipo"] == "derivar_mentoria"]
    publicar = [a for a in acciones if a["tipo"] == "publicar_prioritario"]
    faqs = [a for a in acciones if a["tipo"] == "generar_faq"]

    if alertas:
        lineas.append("")
        lineas.append("🚨 **Miembros en riesgo**")
        for a in alertas:
            lineas.append(
                f"• **{a.get('autor', 'anónimo')}** — riesgo "
                f"{a.get('nivel_riesgo', 0):.0%}: {a.get('accion_sugerida', 'revisar')}"
            )

    if mentorias:
        lineas.append("")
        lineas.append("📚 **Derivaciones a mentoría**")
        for m in mentorias:
            lineas.append(
                f"• {m.get('tema', 'tema')} (×{m.get('veces_detectada', 1)}) "
                f"→ {m.get('mentor_sugerido', 'mentor')}"
            )

    if publicar:
        lineas.append("")
        lineas.append("🚀 **Testimonios para publicar**")
        for p in publicar:
            lineas.append(f"• {p.get('razon', 'testimonio de alto valor')}")

    if faqs:
        lineas.append("")
        lineas.append("❓ **Dudas → FAQ**")
        for f in faqs:
            lineas.append(f"• {f.get('razon', 'duda técnica')}")

    activos = result.get("activos_distribucion_generados") or {}
    if activos:
        lineas.append("")
        lineas.append("📦 **Activos generados**")
        for clave, items in activos.items():
            lineas.append(f"• {clave}: {len(items)}")

    if not acciones:
        lineas.append("")
        lineas.append("✨ Sin acciones automáticas para este lote.")

    return _truncate("\n".join(lineas))


def _truncate(texto: str, limite: int = MAX_DISCORD_MESSAGE) -> str:
    """Recorta el texto al límite de Discord sin partir palabras."""
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3].rstrip() + "…"
