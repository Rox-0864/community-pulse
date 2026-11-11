"""Tests de integración: pipeline completo offline (RuleBasedClient).

Prueban la cadena completa SIN API keys:
ingest → análisis (reglas) → decisiones → generadores → respuesta.

También verifican el contrato dual del client rule-based:
- llamadas SÍNCRONAS (módulos de análisis)
- llamadas ASÍNCRONAS con await (generadores)
"""

import asyncio
import json

import pytest

from src.utils.rule_based import RuleBasedClient
from src.orchestration.pipeline import CommunityPulsePipeline


@pytest.mark.asyncio
async def test_pipeline_end_to_end_offline():
    """
    Cadena completa: testimonio → caso_exito → post LinkedIn,
    duda → faq_tip, con decisiones y resumen ejecutivo.
    """
    pipeline = CommunityPulsePipeline(llm_client=RuleBasedClient())
    resultado = await pipeline.process({
        "origen_comunidad": "discord",
        "periodo_referencia": "Semana_04",
        "interacciones": [
            {
                "autor": "Mariana Souza",
                "texto": "¡Conseguí trabajo como dev de IA! "
                         "El proyecto de LangGraph marcó la diferencia",
            },
            {
                "autor": "Lucas",
                "texto": "No entiendo cómo usar OCI, el tutorial no me sirve",
            },
        ],
    })

    assert resultado["status"] == "exito"
    assert resultado["resumen_comunidad"]["total_interacciones_procesadas"] == 2

    decisiones = resultado["resumen_comunidad"]["decisiones"]
    # Shape correcto (fix del bug: el response pierde las acciones):
    # decisiones = {"resumen_ejecutivo": {...}, "acciones_recomendadas": [...]}
    resumen = decisiones["resumen_ejecutivo"]
    assert resumen["testimonios_destacables"] == 1
    assert resumen["dudas_detectadas"] == 1
    assert resumen["acciones_automaticas"] >= 2
    # Las acciones viajan completas (requerido por el panel de alertas)
    assert any(
        a["tipo"] == "publicar_prioritario"
        for a in decisiones["acciones_recomendadas"]
    )

    # El activo de LinkedIn se generó para el caso de éxito
    assert "casos_exito" in resultado["activos_distribucion_generados"]
    assert resultado["activos_distribucion_generados"]["casos_exito"][0]["tipo"] == "post_linkedin"
    assert "faq_tips" in resultado["activos_distribucion_generados"]


@pytest.mark.asyncio
async def test_faqs_no_duplicados_por_mensaje():
    """
    Dos dudas técnicas distintas deben generar DOS FAQs distintos, uno por
    cada mensaje (no dos FAQs del mismo mensaje).

    Regresión: ``generate_asset_for()`` ignoraba el ``mensaje_id`` de cada
    acción y siempre generaba desde el mensaje de mayor relevancia, así que
    dos acciones ``generar_faq`` producían dos FAQs idénticos (mismo autor).
    """
    pipeline = CommunityPulsePipeline(llm_client=RuleBasedClient())
    resultado = await pipeline.process({
        "origen_comunidad": "discord",
        "periodo_referencia": "Semana_04",
        "interacciones": [
            {"autor": "Lucas", "texto": "No entiendo cómo usar OCI, el tutorial no me sirve"},
            {"autor": "Ana", "texto": "No entiendo cómo estructurar nodos condicionales en LangGraph"},
        ],
    })

    faqs = resultado["activos_distribucion_generados"]["faq_tips"]
    assert len(faqs) == 2
    origenes = {faq["origen"] for faq in faqs}
    assert origenes == {"Duda de Lucas", "Duda de Ana"}
    temas = {faq["tema"] for faq in faqs}
    assert temas == {"oci", "langgraph"}


def test_rule_based_client_contract_sync_and_async():
    """
    El client rule-based soporta las DOS llamadas del codebase:
    - sync: análisis (sentiment/categorization/relevance)
    - async: generadores (await create(...))
    """
    client = RuleBasedClient()
    messages = [
        {"role": "system", "content": "Eres un experto en análisis de sentimiento de comunidades tecnológicas."},
        {"role": "user", "content": "Analiza el sentimiento de este mensaje:\n\nNo me funciona el bucket"},
    ]

    # Uso síncrono (análisis)
    resp = client.chat.completions.create(
        model="x", messages=messages, response_format={"type": "json_object"}
    )
    sent = json.loads(resp.choices[0].message.content)
    assert sent["sentiment"] == "negativo"

    # Uso asíncrono (generadores)
    async def call_async():
        r = await client.chat.completions.create(
            model="x", messages=messages, response_format={"type": "json_object"}
        )
        return json.loads(r.choices[0].message.content)

    result = asyncio.run(call_async())
    assert result["sentiment"] == "negativo"


def test_rule_based_metrics_es():
    """Métricas del cliente rule-based sobre texto positivo fuerte."""
    client = RuleBasedClient()
    resp = client.chat.completions.create(
        model="x",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de sentimiento de comunidades tecnológicas."},
            {"role": "user", "content": "Analiza el sentimiento de este mensaje:\n\nConseguí empleo como dev"},
        ],
    )
    sent = json.loads(resp.choices[0].message.content)
    assert sent["sentiment"] == "muy_positivo"
    assert sent["score"] > 0.8


def test_rule_based_duda_no_es_negativa():
    """
    "no entiendo" es una duda, no un sentimiento negativo ni frustración.

    Regresión: "no entiendo" estaba en NEGATIVO y en DUDA a la vez; como
    NEGATIVO se evaluaba antes, toda duda pura se clasificaba "negativo".
    """
    client = RuleBasedClient()
    resp = client.chat.completions.create(
        model="x",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de sentimiento de comunidades tecnológicas."},
            {"role": "user", "content": "Analiza el sentimiento de este mensaje:\n\nNo entiendo cómo configurar OCI"},
        ],
    )
    sent = json.loads(resp.choices[0].message.content)
    assert sent["sentiment"] == "neutral"


@pytest.mark.asyncio
async def test_duda_pura_no_genera_alerta_miembro():
    """
    Un miembro que solo pide ayuda NO debe marcarse como "en riesgo de abandono".

    Regresión: "no entiendo" sumaba frustración (+0.25) y sentimiento bajo
    (0.3), llevando el riesgo a exactamente 0.60 = umbral de alerta_miembro.
    """
    pipeline = CommunityPulsePipeline(llm_client=RuleBasedClient())
    resultado = await pipeline.process({
        "origen_comunidad": "discord",
        "periodo_referencia": "Semana_04",
        "interacciones": [
            {"autor": "Lucas", "texto": "No entiendo cómo configurar OCI, me pueden ayudar"},
        ],
    })

    decisiones = resultado["resumen_comunidad"]["decisiones"]
    acciones = decisiones["acciones_recomendadas"]

    assert not any(a["tipo"] == "alerta_miembro" for a in acciones)
    assert not any(a["tipo"] == "alerta_sentimiento_puntual" for a in acciones)
    # Sí se detecta como duda técnica → FAQ
    assert any(a["tipo"] == "generar_faq" for a in acciones)


def test_fallback_usa_rule_based_si_primary_falla():
    """El FallbackLLMClient delega en rule_based cuando el principal falla."""
    from src.utils.llm_client import FallbackLLMClient
    from src.utils.rule_based import RuleBasedClient

    class FailingClient:
        """Cliente que simula un LLM sin acceso (sin internet / API caída)."""
        class chat:
            class completions:
                @staticmethod
                def create(model=None, messages=None, response_format=None):
                    raise ConnectionError("sin internet")

    client = FallbackLLMClient(FailingClient(), RuleBasedClient())
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de sentimiento de comunidades tecnológicas."},
            {"role": "user", "content": "Analiza el sentimiento de este mensaje:\n\nNo me funciona el bucket"},
        ],
    )

    sent = json.loads(resp.choices[0].message.content)
    assert sent["sentiment"] == "negativo"