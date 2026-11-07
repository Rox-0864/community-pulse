"""Tests de la lógica pura del bot de Discord (sin conexión real).

Cubren ``build_batch_from_messages`` y ``format_pulse_result`` de
``src/bot/pulse.py``, más el flujo end-to-end con el pipeline offline
(RuleBasedClient). No requieren token ni la librería discord.py.
"""

import pytest

from src.bot.pulse import build_batch_from_messages, format_pulse_result


# ----------------------------------------------------------------------
# Fakes tipo discord.Message (acceso por atributo)
# ----------------------------------------------------------------------
class _FakeAuthor:
    def __init__(self, name, bot=False):
        self.name = name
        self.bot = bot


class _FakeChannel:
    def __init__(self, name):
        self.name = name


class _FakeMessage:
    def __init__(self, content, author="Ana", channel="general", bot=False, created_at=None):
        self.content = content
        self.author = _FakeAuthor(author, bot) if isinstance(author, str) else author
        self.channel = _FakeChannel(channel) if isinstance(channel, str) else channel
        self.created_at = created_at


# ----------------------------------------------------------------------
# build_batch_from_messages
# ----------------------------------------------------------------------
def test_build_batch_maps_discord_message_fields():
    payload = build_batch_from_messages(
        [
            _FakeMessage("¡Conseguí empleo!", "Mariana", "#logros-y-empleos"),
            _FakeMessage("Duda de LangGraph", "Lucas", "#dudas"),
        ],
        periodo="Semana_01",
    )

    assert payload["origen_comunidad"] == "discord"
    assert payload["periodo_referencia"] == "Semana_01"
    assert len(payload["interacciones"]) == 2
    assert payload["interacciones"][0] == {
        "autor": "Mariana",
        "canal": "#logros-y-empleos",
        "texto": "¡Conseguí empleo!",
        "timestamp": "",
    }


def test_build_batch_skips_bot_empty_and_command_messages():
    payload = build_batch_from_messages(
        [
            _FakeMessage("mensaje válido", "Ana"),
            _FakeMessage("", "Ana"),                       # vacío
            _FakeMessage("!pulse", "Ana"),                 # comando del bot
            _FakeMessage("soy un bot", bot=True),          # autor bot
        ]
    )

    assert len(payload["interacciones"]) == 1
    assert payload["interacciones"][0]["texto"] == "mensaje válido"


def test_build_batch_accepts_dicts():
    payload = build_batch_from_messages(
        [
            {"autor": "Ana", "canal": "#general", "texto": "hola", "bot": False},
            {"autor": "Bot", "texto": "auto", "bot": True},
        ]
    )

    assert len(payload["interacciones"]) == 1
    assert payload["interacciones"][0]["autor"] == "Ana"


def test_build_batch_empty_returns_no_interacciones():
    payload = build_batch_from_messages([])
    assert payload["interacciones"] == []


# ----------------------------------------------------------------------
# format_pulse_result
# ----------------------------------------------------------------------
def _result(acciones, activos=None):
    return {
        "status": "exito",
        "resumen_comunidad": {
            "total_interacciones_procesadas": 3,
            "sentimiento_predominante": "positivo",
            "decisiones": {"acciones_recomendadas": acciones},
        },
        "activos_distribucion_generados": activos or {},
    }


def test_format_result_header_and_alerts():
    out = format_pulse_result(
        _result(
            [
                {
                    "tipo": "alerta_miembro",
                    "autor": "João",
                    "nivel_riesgo": 0.67,
                    "accion_sugerida": "contactar_individualmente",
                },
                {
                    "tipo": "publicar_prioritario",
                    "razon": "testimonio con relevancia 0.92",
                },
            ]
        )
    )

    assert "Community Pulse" in out
    assert "Interacciones procesadas: `3`" in out
    assert "Miembros en riesgo" in out
    assert "João" in out
    assert "67%" in out
    assert "Testimonios para publicar" in out


def test_format_result_mentorship_and_assets():
    out = format_pulse_result(
        _result(
            [
                {
                    "tipo": "derivar_mentoria",
                    "tema": "LangGraph",
                    "veces_detectada": 3,
                    "mentor_sugerido": "mentor_orquestacion",
                },
            ],
            activos={"faq_tips": [{}, {}], "casos_exito": [{}]},
        )
    )

    assert "Derivaciones a mentoría" in out
    assert "LangGraph" in out
    assert "Activos generados" in out
    assert "faq_tips: 2" in out
    assert "casos_exito: 1" in out


def test_format_result_no_acciones():
    out = format_pulse_result(_result([]))
    assert "Sin acciones automáticas" in out


def test_format_result_error_status():
    out = format_pulse_result({"status": "error", "error": "boom"})
    assert "El análisis falló" in out
    assert "boom" in out


def test_format_result_truncates_to_discord_limit():
    # 60 acciones → mensaje largo que debe recortarse bajo el límite
    acciones = [
        {"tipo": "generar_faq", "razon": f"duda técnica número {i}" * 3}
        for i in range(200)
    ]
    out = format_pulse_result(_result(acciones))
    assert len(out) <= 1900


# ----------------------------------------------------------------------
# Flujo end-to-end offline
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bot_flow_end_to_end_offline():
    """Mensajes de Discord → payload → pipeline → resumen publicable."""
    from src.orchestration.pipeline import CommunityPulsePipeline
    from src.utils.rule_based import RuleBasedClient

    messages = [
        _FakeMessage(
            "¡Conseguí trabajo como dev de IA! El proyecto de LangGraph marcó la diferencia",
            "Mariana",
            "#logros-y-empleos",
        ),
        _FakeMessage(
            "No entiendo cómo usar el bucket en OCI, ¿alguien tiene un tutorial?",
            "João",
            "#dudas-oci",
        ),
    ]

    payload = build_batch_from_messages(messages, "Semana_Discord")
    pipeline = CommunityPulsePipeline(llm_client=RuleBasedClient())
    resultado = await pipeline.process(payload)

    out = format_pulse_result(resultado)
    assert "Community Pulse" in out
    assert "Interacciones procesadas: `2`" in out
    assert "Testimonios para publicar" in out
    assert "Dudas → FAQ" in out
