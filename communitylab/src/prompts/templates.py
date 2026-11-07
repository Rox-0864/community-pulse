"""
CommunityLab — Helpers para construir prompts.

Responsable: Data Scientists
"""


def build_prompt(system_prompt: str, user_content: str, examples: list = None) -> list[dict]:
    """Construye el array de mensajes para el LLM."""
    messages = [{"role": "system", "content": system_prompt}]

    if examples:
        for ex in examples:
            messages.append({"role": "user", "content": ex["input"]})
            messages.append({"role": "assistant", "content": ex["output"]})

    messages.append({"role": "user", "content": user_content})
    return messages


def build_analysis_prompt(text: str, context: dict = None) -> str:
    """Arma el prompt para análisis con contexto adicional."""
    base = f"Analiza el siguiente mensaje de la comunidad:\n\n{text}"
    if context:
        base += f"\n\nContexto adicional:\n- Canal: {context.get('canal', 'desconocido')}"
        base += f"\n- Autor: {context.get('autor', 'desconocido')}"
        base += f"\n- Reacciones: {context.get('reacciones', 0)}"
    return base
