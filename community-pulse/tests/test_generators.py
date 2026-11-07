"""Tests de los generadores de activos de marketing (async).

Cubre: faq_generator.py, linkedin_generator.py, newsletter_generator.py
y testimonial_generator.py.
"""

import pytest

from src.generators.faq_generator import generate_faq_tip
from src.generators.linkedin_generator import generate_linkedin_post
from src.generators.newsletter_generator import generate_newsletter
from src.generators.testimonial_generator import generate_testimonial


@pytest.mark.asyncio
async def test_generate_faq_tip(fake_llm):
    llm = fake_llm({
        "tema": "OCI",
        "titulo": "Tip rápido: OCI",
        "explicacion": "paso a paso",
        "ejemplo": "código",
        "referencia": "https://docs.oracle.com",
    })
    analysis = {
        "texto": "no entiendo OCI",
        "analisis": {"temas": ["duda_tecnica"]},
        "autor": "Lucas",
    }
    result = await generate_faq_tip(analysis, llm)

    assert result["tipo"] == "faq_tip"
    assert result["tema"] == "OCI"
    assert result["titulo_tip"] == "Tip rápido: OCI"
    assert result["explicacion"] == "paso a paso"
    assert result["referencia"] == "https://docs.oracle.com"
    assert result["origen"] == "Duda de Lucas"


@pytest.mark.asyncio
async def test_generate_faq_tip_autor_default(fake_llm):
    llm = fake_llm({"tema": "x"})
    analysis = {"texto": "duda"}
    result = await generate_faq_tip(analysis, llm)
    assert result["origen"] == "Duda de miembro de la comunidad"


@pytest.mark.asyncio
async def test_generate_linkedin_post(fake_llm):
    llm = fake_llm({
        "titulo": "Un logro que inspira",
        "copy": "post copy",
        "potencial_engagement": "Alto",
        "hashtags": ["#OracleONE", "#IA"],
        "mejor_hora_publicacion": "Martes 9am",
    })
    analysis = {
        "texto": "conseguí trabajo",
        "autor": "Mariana",
        "analisis": {
            "sentimiento": {"etiqueta": "positivo"},
            "temas": ["contratacion_logro"],
        },
    }
    result = await generate_linkedin_post(analysis, llm)

    assert result["tipo"] == "post_linkedin"
    assert result["titulo"] == "Un logro que inspira"
    assert result["copy"] == "post copy"
    assert result["canal_recomendado"] == "LinkedIn Oficial"
    assert result["potencial_engagement"] == "Alto"
    assert result["hashtags"] == ["#OracleONE", "#IA"]
    assert result["mejor_hora_publicacion"] == "Martes 9am"


@pytest.mark.asyncio
async def test_generate_newsletter(fake_llm):
    llm = fake_llm({
        "titular": "Destaque de la semana",
        "resumen": "resumen ejecutivo",
        "quote": "cita del miembro",
    })
    analysis = {
        "texto": "texto",
        "autor": "Ana",
        "analisis": {
            "temas": ["testimonio"],
            "relevancia_marketing": {"score": 0.8},
        },
    }
    result = await generate_newsletter(analysis, llm)

    assert result["tipo"] == "newsletter_highlight"
    assert result["seccion"] == "Destaque de la Semana"
    assert result["titular"] == "Destaque de la semana"
    assert result["resumen"] == "resumen ejecutivo"
    assert result["quote"] == "cita del miembro"


@pytest.mark.asyncio
async def test_generate_testimonial(fake_llm):
    llm = fake_llm({
        "titulo": "El viaje de João",
        "narrativa": "historia de superación",
        "resultado": "logro concreto",
        "cta": "¿Te sumás?",
    })
    analysis = {
        "texto": "historia",
        "autor": "João",
        "analisis": {"sentimiento": {"etiqueta": "muy_positivo"}},
    }
    result = await generate_testimonial(analysis, llm)

    assert result["tipo"] == "caso_exito"
    assert result["titulo"] == "El viaje de João"
    assert result["narrativa"] == "historia de superación"
    assert result["resultado"] == "logro concreto"
    assert result["cta"] == "¿Te sumás?"


@pytest.mark.asyncio
async def test_generador_linkedin_defaults_con_payload_vacio(fake_llm):
    """Un payload vacío aplica los defaults del generador."""
    llm = fake_llm({})
    result = await generate_linkedin_post({"texto": "x"}, llm)

    assert result["titulo"] == ""
    assert result["copy"] == ""
    assert result["hashtags"] == []
    assert result["canal_recomendado"] == "LinkedIn Oficial"
    assert result["potencial_engagement"] == "Medio"
