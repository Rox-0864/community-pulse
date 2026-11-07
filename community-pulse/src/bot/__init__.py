"""Bot de Discord para Community Pulse.

Expone la lógica pura (``pulse.py``) para su importación y tests.
La integración con discord.py vive en ``discord_bot.py``.
"""

from src.bot.pulse import DEFAULT_LIMIT, build_batch_from_messages, format_pulse_result

__all__ = [
    "build_batch_from_messages",
    "format_pulse_result",
    "DEFAULT_LIMIT",
]
