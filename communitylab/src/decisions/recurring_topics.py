"""
Community Pulse — Detector de dudas recurrentes.

Detecta cuándo la MISMA duda técnica aparece repetidamente.
Responsable: Data Scientist 2
"""

from collections import Counter


class RecurringTopicsDetector:
    """Detecta dudas técnicas que se repiten en el tiempo."""

    UMBRAL_REPETICION = 3  # misma duda 3+ veces = recurrente

    # Mapa tema → mentor especialista
    AREAS = {
        "langgraph": "especialista_langgraph",
        "langchain": "especialista_langchain",
        "oci": "especialista_oracle_cloud",
        "oracle": "especialista_oracle_cloud",
        "python": "mentor_python",
        "prompt": "especialista_ia",
        "gemini": "especialista_ia",
        "openai": "especialista_ia",
        "streamlit": "especialista_frontend",
        "docker": "especialista_devops",
        "deploy": "especialista_devops",
    }

    def __init__(self, umbral: int = UMBRAL_REPETICION):
        self.umbral = umbral

    def detect(self, mensajes_lote: list[dict], dudas_historial: list[dict]) -> list[dict]:
        """
        Detecta dudas recurrentes combinando el lote actual con el historial.

        Estrategia:
        1. Extraer temas de los mensajes con categoría duda_tecnica
        2. Contar frecuencias en el lote actual
        3. Sumar con frecuencias del historial
        4. Temas con >= umbral = recurrente
        """
        # 1 y 2: Contar temas en el lote actual
        temas_lote = Counter()
        for msg in mensajes_lote:
            if self._es_duda_tecnica(msg):
                for tema in self._extract_temas(msg):
                    if tema:
                        temas_lote[tema.lower()] += 1

        # 3: Sumar historial
        temas_historial = Counter()
        for duda in dudas_historial:
            temas_historial[duda.get("tema", "").lower()] += duda.get("veces", 1)

        temas_totales = temas_lote + temas_historial

        # 4: Filtrar recurrentes
        recurrentes = []
        for tema, veces in temas_totales.items():
            if veces >= self.umbral and tema:
                recurrentes.append({
                    "tema": tema,
                    "veces_detectada": veces,
                    "mentor_sugerido": self._suggest_mentor(tema),
                    "nivel_urgencia": "ALTO" if veces >= 5 else "MEDIO",
                    "accion": "generar_faq_y_derivar"
                })

        return recurrentes

    def _es_duda_tecnica(self, msg: dict) -> bool:
        """¿El mensaje es una duda técnica? Tolera formato plano y anidado.

        Criterio: categoria_sugerida == "faq_tip" o el tema "duda_tecnica"
        en la lista de temas (plano o bajo msg["analisis"]["temas"]).
        """
        categoria = msg.get("categoria_sugerida")
        if categoria is None:
            categoria = (msg.get("analisis") or {}).get("categoria_sugerida")
        if categoria == "faq_tip":
            return True

        # Leer temas LITERALES (sin la derivación de _extract_temas,
        # que llama a _es_duda_tecnica → evita recursión infinita)
        temas = msg.get("temas")
        if temas is None:
            temas = (msg.get("analisis") or {}).get("temas") or []
        if isinstance(temas, dict):
            temas = temas.get("categorias", [])
        if not isinstance(temas, list):
            return False
        return "duda_tecnica" in [t.lower() for t in temas if isinstance(t, str)]

    def _extract_temas(self, msg: dict) -> list[str]:
        """Extrae la lista de temas tolerando formato plano y anidado.

        Mejora: si la duda es técnica pero solo tiene el tema GENÉRICO
        (e.g. "duda_tecnica" — lo que produce el categorizador), se deriva
        la TECNOLOGÍA real del texto (e.g. "langgraph"). Sin esto, dos
        mensajes sobre langgraph NO suman recurrencia contra el historial.
        """
        temas = msg.get("temas") or []
        if isinstance(temas, list):
            lista = [t for t in temas if isinstance(t, str)]
        elif isinstance(temas, dict):  # orchestration: {categorias: [...]}
            lista = [t for t in temas.get("categorias", []) if isinstance(t, str)]
        else:
            lista = []

        if self._es_duda_tecnica(msg):
            tecnologia = self._detect_tech(msg.get("texto", ""))
            if tecnologia:
                lista.append(tecnologia)

        return lista

    def _detect_tech(self, texto: str) -> str:
        """Detecta qué tecnología menciona el texto (claves de AREAS)."""
        t = texto.lower()
        for tech in self.AREAS:
            if tech in t:
                return tech
        return ""

    def _suggest_mentor(self, tema: str) -> str:
        """Sugiere qué especialista debería atender la duda."""
        for key, mentor in self.AREAS.items():
            if key in tema.lower():
                return mentor
        return "mentor_general"