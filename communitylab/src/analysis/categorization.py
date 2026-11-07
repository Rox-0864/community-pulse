"""
CommunityLab — Categorización de temas con LLM.

Responsable: Data Scientist 2
"""

import json

CATEGORIAS_DISPONIBLES = [
    "contratacion_logro",
    "duda_tecnica",
    "feedback_positivo",
    "feedback_negativo",
    "sugerencia",
    "testimonio",
    "general",
]


def categorize_message(text: str, canal: str, llm_client) -> list[dict]:
    """
    Categoriza un mensaje en temas predefinidos.
    """
    prompt = f"""Categoriza este mensaje de la comunidad en UNA o MÁS categorías.

Canal: {canal}
Mensaje: {text}

Categorías disponibles:
- contratacion_logro: logros laborales, entrevistas, contrataciones
- duda_tecnica: preguntas sobre código, herramientas, conceptos
- feedback_positivo: elogios, agradecimientos, experiencias buenas
- feedback_negativo: quejas, problemas, dificultades
- sugerencia: ideas de mejora, peticiones de features
- testimonio: historias personales de superación
- general: conversación casual, off-topic

Retorna JSON con: categorias (lista de strings), confianza (float)
"""
    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un clasificador de contenido de comunidades."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("categorias", [])
