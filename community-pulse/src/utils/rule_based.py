"""
Community Pulse — Cliente LLM basado en reglas (modo offline/demo).

Implementa la MISMA interfaz que el LLM real (chat.completions.create)
pero decide con reglas deterministas. Permite ejecutar el pipeline
completo SIN API keys — ideal para demos, tests y CI.

¿Por qué una respuesta auto-awaitable?
El codebase llama al LLM de DOS formas inconsistentes:
- Módulos de análisis (sentiment/categorization/relevance): SINCRÓNICO
    response = llm_client.chat.completions.create(...)
- Generadores (linkedin/faq/newsletter/testimonio): ASINCRÓNICO
    response = await llm_client.chat.completions.create(...)

RuleBasedResponse implementa __await__ devolviéndose a sí mismo, así
funciona en AMBOS contextos:
- Uso sync: response.choices[0].message.content → directo
- Uso async: await response → devuelve el mismo objeto → .choices[...]

⚠️ Nota para el equipo: hay que unificar la interfaz del cliente LLM en
los generadores (await) y en los módulos de análisis (sin await). Este
adapter es un puente, no la solución permanente.

Responsable: Software Engineer
"""

import json
import re


# ----------------------------------------------------------------------
# Señales de reglas (textos en español = idioma de la comunidad)
# ----------------------------------------------------------------------
NEGATIVO_FUERTE = [
    "me rindo", "abandonar", "terrible", "odio", "horrible", "peor experiencia",
]
NEGATIVO = [
    "no funciona", "no me funciona", "no funca", "error", "bug", "no puedo",
    "no me sirve", "trabado", "frustrad", "no anda",
    "falla", "rompió", "no carga", "no deja", "problema", "issue",
]
CONTRATACION = [
    "conseguí trabajo", "quede seleccionad", "seleccionad", "contratad",
    "empleo", "trabajo como",
]
LOGROS = [
    "logré", "logre", "aprobar", "certific", "orgullos", "acredit",
    "termine", "terminé", "finalicé", "concluí", "🎉",
]
POSITIVO_FUERTE = CONTRATACION + LOGROS
POSITIVO = [
    "gracias", "increíble", "genial", "excelente", "espectacular",
    "me ayudó", "aprendí", "recomiendo", "me encantó", "me sirvió",
    "me sirvieron", "buenísimo", "buenisimo", "fantástico",
]
DUDA = [
    "cómo hago", "cómo uso", "no entiendo", "alguien sabe", "tutorial",
    "ejemplo de", "pueden ayudar", "duda", "consulta", "cómo se hace",
    "por qué",
]


class RuleBasedResponse:
    """Respuesta que funciona en llamadas sync y async (ver docstring)."""

    def __init__(self, content: str):
        class _Message:
            def __init__(self, content: str):
                self.content = content

        class _Choice:
            def __init__(self, content: str):
                self.message = _Message(content)

        self.choices = [_Choice(content)]

    def __await__(self):
        """Permite `await create(...)` sin romper el uso sincrónico."""
        async def _wrap():
            return self
        return _wrap().__await__()


class RuleBasedChat:
    """Adapter de chat.completions based on rules."""

    # Marcador de system prompt → handler
    DISPATCH = [
        ("análisis de sentimiento", "sentiment"),
        ("clasificador de contenido", "categories"),
        ("editor de contenido de marketing tech", "relevance"),
        ("copywriter experto en LinkedIn", "linkedin"),
        ("mentor técnico", "faq"),
        ("editor de newsletters tech", "newsletter"),
        ("storyteller de casos de éxito", "testimonial"),
    ]

    def create(self, model: str = None, messages: list = None, response_format: dict = None):
        """Retorna una respuesta JSON determinista según el system prompt."""
        system_prompt = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        user_content = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )

        tipo = self._detect(system_prompt)
        payload = self._handle(tipo, user_content)
        return RuleBasedResponse(json.dumps(payload, ensure_ascii=False))

    # ------------------------------------------------------------------
    def _detect(self, system_prompt: str) -> str:
        for marker, tipo in self.DISPATCH:
            if marker in system_prompt:
                return tipo
        return "generic"

    def _handle(self, tipo: str, prompt: str) -> dict:
        handlers = {
            "sentiment": self._sentiment,
            "categories": self._categories,
            "relevance": self._relevance,
            "linkedin": self._linkedin,
            "faq": self._faq,
            "newsletter": self._newsletter,
            "testimonial": self._testimonial,
            "generic": lambda p: {"ok": True},
        }
        return handlers[tipo](prompt)

    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def _sentiment(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        neg_fuerte = self._hits(texto, NEGATIVO_FUERTE)
        neg = self._hits(texto, NEGATIVO)
        pos_fuerte = self._hits(texto, POSITIVO_FUERTE)
        pos = self._hits(texto, POSITIVO)
        duda = self._hits(texto, DUDA)

        if neg_fuerte or (neg and not pos_fuerte and not pos):
            etiqueta, score = ("muy_negativo", 0.1) if neg_fuerte else ("negativo", 0.3)
        elif pos_fuerte:
            etiqueta, score = "muy_positivo", 0.92
        elif pos:
            etiqueta, score = "positivo", 0.72
        elif duda:
            etiqueta, score = "neutral", 0.5
        else:
            etiqueta, score = "neutral", 0.5

        emociones = {
            "muy_positivo": "orgullo", "positivo": "alegría",
            "negativo": "frustración", "muy_negativo": "frustración",
            "neutral": "neutral",
        }
        return {
            "sentiment": etiqueta,
            "score": score,
            "confidence": 0.7,
            "emotion_detected": emociones[etiqueta],
            "keywords": (neg_fuerte + neg + pos_fuerte + pos)[:5],
        }

    def _categories(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        categorias = []
        if self._hits(texto, DUDA):
            categorias.append("duda_tecnica")
        if self._hits(texto, CONTRATACION):
            categorias.append("contratacion_logro")
        if self._hits(texto, LOGROS + CONTRATACION):
            categorias.append("testimonio")
        if self._hits(texto, POSITIVO):
            categorias.append("feedback_positivo")
        if self._hits(texto, NEGATIVO + NEGATIVO_FUERTE):
            categorias.append("feedback_negativo")
        if not categorias:
            categorias.append("general")
        return {"categorias": categorias, "confianza": 0.7}

    def _relevance(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        etiqueta = self._sentiment(prompt)["sentiment"]
        cats = self._categories(prompt)["categorias"]

        score = 0.4
        if etiqueta == "muy_positivo":
            score += 0.25
        elif etiqueta == "positivo":
            score += 0.15
        elif etiqueta in ("negativo", "muy_negativo"):
            score -= 0.1
        if "contratacion_logro" in cats or "testimonio" in cats:
            score += 0.2
        if "duda_tecnica" in cats:
            score += 0.15
        score = round(min(max(score, 0.05), 0.98), 2)

        return {
            "shareability": score,
            "emotion": 0.7 if etiqueta.startswith(("muy_", "pos")) else 0.4,
            "inspiration": 0.8 if "testimonio" in cats else 0.3,
            "brand_alignment": 0.7,
            "promedio_ponderado": score,
            "justificacion": f"Reglas offline: sentimiento {etiqueta}, categorías {cats}",
        }

    # ------------------------------------------------------------------
    # Generadores (templates deterministas)
    # ------------------------------------------------------------------
    def _linkedin(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        autor = self._extract(prompt, "Autor", "Sentimiento") or "miembro"
        return {
            "titulo": f"{autor}: un logro que inspira a la comunidad",
            "copy": (
                f"🚀 {texto[:200]}\n\n"
                "Esta historia demuestra el poder de una comunidad que "
                "aprende junta. ¿Qué logro conseguiste esta semana?\n\n"
                "#OracleONE #InteligenciaArtificial #ComunidadTech"
            ),
            "potencial_engagement": "Alto",
            "hashtags": ["#OracleONE", "#IA", "#ComunidadTech"],
            "mejor_hora_publicacion": "Martes 9am-11am",
        }

    def _faq(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        # El prompt de FAQ trae "Tema: ['duda_tecnica', ...]" (lista Python
        # serializada) — no sirve como título. Mejor detectar el tema real.
        tema = self._detect_tema(texto)
        return {
            "tema": tema,
            "titulo": f"Tip rápido: {tema}",
            "explicacion": (
                f"Para resolver la duda \"{texto[:80]}\", revisá la "
                "documentación oficial, dividí el problema en pasos y "
                "probá en un entorno de prueba."
            ),
            "ejemplo": "Fragmento de código de ejemplo disponible en docs oficiales.",
            "referencia": "https://docs.oracle.com",
        }

    def _newsletter(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        return {
            "seccion": "Destaque de la Semana",
            "titular": texto[:60],
            "resumen": "Miembro de la comunidad compartió una historia destacable esta semana.",
            "quote": texto[:120],
            "enlace_sugerido": "",
        }

    def _testimonial(self, prompt: str) -> dict:
        texto = self._message_text(prompt)
        autor = self._extract(prompt, "Autor") or "miembro"
        return {
            "titulo": f"El viaje de {autor}",
            "narrativa": f"{texto[:200]}",
            "resultado": "Logro concreto alcanzado dentro del programa",
            "cta": "¿Te sumás al próximo desafío de la comunidad?",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _message_text(self, prompt: str) -> str:
        """Extrae el texto del mensaje del user prompt.

        Casos:
        - "Mensaje original: X" / "Duda original: X" / "Mensaje: X" (misma línea)
        - Sentimiento: "Analiza el sentimiento de este mensaje:\n\n<texto>"
          (el texto va en la línea siguiente al encabezado)
        """
        lineas = prompt.splitlines()
        for i, linea in enumerate(lineas):
            s = linea.strip()
            for key in ("Mensaje original:", "Duda original:", "Mensaje:"):
                if s.startswith(key):
                    return s[len(key):].strip()
            if "Analiza el sentimiento de este mensaje:" in s:
                return "\n".join(lineas[i + 1:]).strip()
        return prompt

    def _extract(self, prompt: str, key: str, stop: str = None) -> str:
        """Extrae el valor de 'key: valor...' hasta el próximo campo o fin."""
        m = re.search(rf"{key}:\s*(.+)", prompt)
        if not m:
            return ""
        valor = m.group(1).strip()
        if stop:
            # Cortar en la clave de parada (aparece en otra línea)
            valor = re.split(rf"\n\s*{stop}:", valor)[0]
        return valor.strip()

    def _detect_tema(self, texto: str) -> str:
        """Detecta el tema técnico de una duda (para títulos legibles)."""
        t = texto.lower()
        for tema in (
            "langgraph", "langchain", "streamlit", "docker", "gemini",
            "oracle", "oci", "prompt", "python", "openai",
        ):
            if tema in t:
                return tema
        return texto[:40] or "duda técnica"

    def _hits(self, texto: str, keywords: list) -> list:
        t = texto.lower()
        return [k for k in keywords if k.lower() in t]


class RuleBasedClient:
    """Punto de entrada compatible con la interfaz del pipeline."""

    class chat:
        class completions:
            create = RuleBasedChat().create