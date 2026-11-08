"""
Community Pulse — Generador de posts para LinkedIn.

Responsable: Software Engineer + Data Scientists
"""

import json

from src.prompts.linkedin_prompts import LINKEDIN_SYSTEM_PROMPT
from src.prompts.templates import build_prompt


async def generate_linkedin_post(analysis: dict, llm_client) -> dict:
    """Genera un post de LinkedIn a partir del análisis de un mensaje."""
    message_text = analysis.get("texto", "")
    sentimiento = analysis.get("analisis", {}).get("sentimiento", {}).get("etiqueta", "neutral")
    temas = analysis.get("analisis", {}).get("temas", [])

    user_prompt = f"""Genera un post de LinkedIn basado en este mensaje de la comunidad:

Mensaje original: {message_text}
Autor: {analysis.get('autor', 'miembro de la comunidad')}
Sentimiento detectado: {sentimiento}
Temas relevantes: {temas}

El post debe:
1. Tener un gancho fuerte en la primera línea
2. Contar la historia de forma inspiradora
3. Incluir un call-to-action
4. Tener 3-5 hashtags relevantes
5. Máximo 1300 caracteres (límite de LinkedIn)
"""
    messages = build_prompt(LINKEDIN_SYSTEM_PROMPT, user_prompt)

    response = await llm_client.chat.completions.create(
        messages=messages,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "tipo": "post_linkedin",
        "titulo": result.get("titulo", ""),
        "copy": result.get("copy", ""),
        "canal_recomendado": "LinkedIn Oficial",
        "potencial_engagement": result.get("potencial_engagement", "Medio"),
        "hashtags": result.get("hashtags", []),
        "mejor_hora_publicacion": result.get("mejor_hora_publicacion", ""),
    }
