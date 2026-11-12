"""
Community Pulse — Puntuación de relevancia para marketing.

Responsable: Data Scientist 3
"""

import json


def _extraer_score(result: dict) -> float:
    """Extrae el score de relevancia tolerando claves en español e inglés.

    Groq (y otros modelos) a veces devuelven ``weighted_average`` en inglés
    en vez de ``promedio_ponderado``; este helper degrada con gracia si la
    clave esperada no está, en vez de quedarse clavado en el default 0.5.
    """
    for key in ("promedio_ponderado", "weighted_average", "promedio", "average", "score"):
        if key in result and result[key] is not None:
            try:
                return float(result[key])
            except (TypeError, ValueError):
                continue
    return 0.5


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

Retorna SOLO un JSON con las claves exactas: "shareability", "emotion",
"inspiration", "brand_alignment" (números 0-1), "promedio_ponderado"
(número 0-1, el promedio ponderado) y "justificacion" (string breve).
"""
    response = llm_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Eres un editor de contenido de marketing tech."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return {
        "score": _extraer_score(result),
        "desglose": result,
        "razon": result.get(
            "justificacion",
            result.get("justification", result.get("razon", result.get("reason", ""))),
        ),
    }
