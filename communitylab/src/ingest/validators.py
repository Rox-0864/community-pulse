"""
CommunityLab — Validación de mensajes.

Responsable: Software Engineer
"""

from pydantic import BaseModel, Field
from typing import Optional


class MessageSchema(BaseModel):
    id: str
    autor: str
    canal: str
    tipo: str = Field(
        default="general",
        pattern="^(testimonio|pregunta_tecnica|feedback|logro|general|sugerencia)$",
    )
    texto: str = Field(..., min_length=10, max_length=5000)
    timestamp: str
    origen: str
    metadata: Optional[dict] = None


def validate_message(message: dict) -> bool:
    """Valida que un mensaje cumple el esquema."""
    try:
        MessageSchema(**message)
        return True
    except Exception:
        return False


def validate_batch(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Retorna (válidos, inválidos)."""
    validos = []
    invalidos = []
    for msg in messages:
        if validate_message(msg):
            validos.append(msg)
        else:
            invalidos.append(msg)
    return validos, invalidos
