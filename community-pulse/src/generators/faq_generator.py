"""
Community Pulse — Generador de FAQ / Tip rápido.

Responsable: Data Analyst 2 + Data Scientists
"""

import json

from src.prompts.faq_prompts import FAQ_SYSTEM_PROMPT
from src.prompts.templates import build_prompt


async def generate_faq_tip(analysis: dict, llm_client) -> dict:
    """Genera un FAQ o Tip rápido a partir de una duda frecuente."""
    prompt = f"""Crea un "Tip Rápido" para la comunidad:

Duda original: {analysis.get('texto')}
Tema: {analysis.get('analisis', {}).get('temas')}
Autor: {analysis.get('autor')}
"""
    messages = build_prompt(FAQ_SYSTEM_PROMPT, prompt)

    response = await llm_client.chat.completions.create(
        messages=messages,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "tipo": "faq_tip",
        "tema": result.get("tema", ""),
        "titulo_tip": result.get("titulo", ""),
        "explicacion": result.get("explicacion", ""),
        "ejemplo": result.get("ejemplo", ""),
        "referencia": result.get("referencia", ""),
        "origen": f"Duda de {analysis.get('autor', 'miembro de la comunidad')}",
    }
