"""
CommunityLab — Puntuación de relevancia para marketing.

Responsable: Data Scientist 3
"""

import json


def score_relevance(text: str, analisis_previo: dict, llm_client) -> dict:
    """
    Puntúa qué tan relevante es un mensaje para marketing.
    """
    prompt = f"""Evalúa qué tan relevante es este mensaje para crear contenido de marketing.

Mensaje: {text}
Sentimiento detectado: {analisis_previo.get('sentimiento', {}).get('etiqueta')}
Categorías: {analisis_previo.get('categorias')}

Califica del 0 al 1:
- shareability: ¿Lo compartirías en redes?
- emotion: ¿Genera emoción?
- inspiration: ¿Inspira a otros?
- brand_alignment: ¿Alineado con la marca?

Retorna JSON con scores individuales, promedio ponderado y justificación.
"""
    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un editor de contenido de marketing tech."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "score": float(result.get("promedio_ponderado", result.get("score", 0.5))),
        "desglose": result,
        "razon": result.get("justificacion", result.get("razon", "")),
    }
