"""
Community Pulse — Normalización de mensajes al formato estándar.

Convierte mensajes de cualquier fuente (Discord, Slack, CSV, JSON)
al formato interno del sistema.
Responsable: Data Analysts
"""

from datetime import datetime

# Mapa de canales a categorías (ajustar según la fuente de datos real)
CHANNEL_MAP = {
    "#logros-y-empleos": "logro",
    "#logros": "logro",
    "#dudas-langgraph": "pregunta_tecnica",
    "#dudas": "pregunta_tecnica",
    "#feedback-cursos": "feedback",
    "#feedback": "feedback",
    "#general": "general",
    "general": "general",
}


def normalize_message(raw: dict, origen: str = "discord") -> dict:
    """Normaliza un mensaje al formato estándar del sistema."""
    texto = raw.get("texto", raw.get("content", raw.get("body", ""))).strip()
    if not texto:
        texto = raw.get("title", raw.get("review", "")).strip()

    return {
        "id": raw.get("id", f"msg_{abs(hash(texto)) % 100000:05d}"),
        "autor": raw.get("autor", raw.get("author", raw.get("username", "Anónimo"))),
        "canal": raw.get("canal", raw.get("channel", "general")),
        "tipo": CHANNEL_MAP.get(
            raw.get("canal", raw.get("channel", "")),
            raw.get("tipo", raw.get("label", "general")),
        ),
        "texto": texto,
        "timestamp": raw.get("timestamp", raw.get("created_at", datetime.now().isoformat())),
        "origen": origen,
        "metadata": {
            "score": raw.get("score", raw.get("upvotes", 0)),
            "reacciones": raw.get("reacciones", raw.get("reactions", 0)),
        },
    }


def normalize_batch(messages: list[dict], origen: str = "discord") -> list[dict]:
    """Normaliza un lote de mensajes."""
    return [m for m in (normalize_message(msg, origen) for msg in messages) if m["texto"]]