"""
Community Pulse — Generador de destaque para Newsletter.

Responsable: Software Engineer + Data Scientists
"""

import json

from src.prompts.newsletter_prompts import NEWSLETTER_SYSTEM_PROMPT
from src.prompts.templates import build_prompt


async def generate_newsletter(analysis: dict, llm_client) -> dict:
    """Genera una sección de newsletter semanal."""
    prompt = f"""Crea una sección de "Destaque de la Semana" para newsletter:

Mensaje: {analysis.get('texto')}
Tema: {analysis.get('analisis', {}).get('temas')}
Relevancia: {analysis.get('analisis', {}).get('relevancia_marketing', {}).get('score', 0)}
Autor: {analysis.get('autor')}

Formato:
- Titular (máx 60 chars)
- Resumen ejecutivo (2-3 oraciones)
- Quote del miembro (si aplica)
"""
    messages = build_prompt(NEWSLETTER_SYSTEM_PROMPT, prompt)

    response = await llm_client.chat.completions.create(
        messages=messages,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "tipo": "newsletter_highlight",
        "seccion": "Destaque de la Semana",
        "titular": result.get("titular", ""),
        "resumen": result.get("resumen", ""),
        "quote": result.get("quote", ""),
    }
