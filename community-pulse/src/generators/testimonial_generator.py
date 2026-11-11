"""
Community Pulse — Generador de casos de éxito / testimonios.

Responsable: Data Scientist 3
"""

import json


async def generate_testimonial(analysis: dict, llm_client) -> dict:
    """Genera un caso de éxito/testimonio formateado."""
    prompt = f"""Crea un testimonio formateado para marketing:

Mensaje original: {analysis.get('texto')}
Autor: {analysis.get('autor')}
Sentimiento: {analysis.get('analisis', {}).get('sentimiento', {}).get('etiqueta')}

Formato:
- Título del caso
- Narrativa (3-4 oraciones)
- Resultado concreto
- CTA para la comunidad
"""
    response = await llm_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un storyteller de casos de éxito tech.\n\n"
                    "## Formato de respuesta (SOLO JSON):\n"
                    "{\n"
                    '  "titulo": "Título del caso",\n'
                    '  "narrativa": "3-4 oraciones",\n'
                    '  "resultado": "resultado concreto",\n'
                    '  "cta": "llamado a la acción para la comunidad"\n'
                    "}"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "tipo": "caso_exito",
        "titulo": result.get("titulo", ""),
        "narrativa": result.get("narrativa", ""),
        "resultado": result.get("resultado", ""),
        "cta": result.get("cta", ""),
    }
