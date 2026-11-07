"""
CommunityLab — Ingestión de datos de la comunidad.

Carga archivos (JSON/CSV), normaliza al formato estándar y valida.
Responsable: Data Analysts + Software Engineer
"""

import json
import csv
from pathlib import Path
from typing import Optional


def load_json(filepath: str) -> list[dict]:
    """Carga un archivo JSON con mensajes de la comunidad."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    return data.get("interacciones", [])


def load_csv(filepath: str) -> list[dict]:
    """Carga un CSV y lo convierte a lista de diccionarios."""
    messages = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)
    return messages


def load_community_data(filepath: str) -> list[dict]:
    """Detecta el formato y carga automáticamente."""
    path = Path(filepath)
    if path.suffix == ".json":
        return load_json(filepath)
    elif path.suffix == ".csv":
        return load_csv(filepath)
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")