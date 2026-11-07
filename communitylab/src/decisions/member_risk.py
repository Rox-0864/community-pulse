"""
CommunityLab — Detector de miembros en riesgo de abandono.

Monitorea la trayectoria de sentimiento de cada miembro.
Responsable: Data Scientist 1
"""

from src.decisions.prompts import RISK_ANALYSIS_PROMPT


class MemberRiskDetector:
    """Detecta miembros en riesgo de abandonar la comunidad."""

    # Umbrales de riesgo
    UMBRAL_RECIENTE_NEGATIVO = 2   # ≥2 mensajes negativos recientes
    UMBRAL_CAIDA_EMOCIONAL = 0.4   # caída de score ≥ 0.4 vs promedio histórico
    UMBRAL_ALERTA = 0.6            # nivel de riesgo para generar alerta

    FRUSTRACION_KEYWORDS = [
        "no funciona", "no puedo", "error", "bug", "frustrado", "frustrada",
        "me rindo", "abandonar", "no entiendo", "no me sirve",
        "horrible", "terrible", "perdido", "perdida", "trabado", "trabada", "bloqueado", "bloqueada",
    ]

    def __init__(self, llm_client, historial: dict):
        self.llm = llm_client
        self.historial = historial

    def evaluate_author(self, autor: str, mensajes_lote: list[dict]) -> dict:
        """
        Evalúa el nivel de riesgo de abandonar la comunidad para un autor.

        Combina 3 señales:
        S1: Sentimiento promedio reciente del autor
        S2: Tendencia vs historial previo (¿está cayendo?)
        S3: Contenido de los mensajes (¿problemas bloqueantes?)
        """
        # S1: Sentimiento promedio del lote actual
        sentimiento_reciente = self._average_sentiment(mensajes_lote)

        # S2: Comparar con historial (si existe)
        historial_autor = self.historial.get("miembros_tracking", {}).get(autor, {})
        sentimiento_historico = historial_autor.get("sentimiento_promedio", 0.5)

        caida = sentimiento_historico - sentimiento_reciente

        # S3: Detectar señales de frustración en el texto
        frustacion = self._detect_frustration(mensajes_lote)

        # Calcular nivel de riesgo (0-1)
        nivel_riesgo = self._compute_risk_level(
            sentimiento_reciente,
            caida,
            frustacion
        )

        razon = self._build_reason(
            autor, sentimiento_reciente, caida, frustacion, nivel_riesgo
        )

        accion = "contactar_individualmente" if nivel_riesgo >= self.UMBRAL_ALERTA else "monitorear"

        return {
            "autor": autor,
            "nivel_riesgo": round(nivel_riesgo, 2),
            "razon": razon,
            "accion_sugerida": accion,
            "senales": {
                "sentimiento_reciente": round(sentimiento_reciente, 2),
                "caida_vs_historial": round(caida, 2),
                "frustracion_detectada": frustacion
            }
        }

    def _average_sentiment(self, mensajes: list[dict]) -> float:
        """Promedio de scores de sentimiento de los mensajes.

        Tolerante: el score puede estar en msg["sentimiento"]["score"]
        (formato análisis) o msg["analisis"]["sentimiento"]["score"] (orchestrator).
        """
        scores = []
        for m in mensajes:
            sent = m.get("sentimiento") or (m.get("analisis") or {}).get("sentimiento") or {}
            score = sent.get("score", 0.5)
            if isinstance(score, (int, float)):
                scores.append(score)
        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _detect_frustration(self, mensajes: list[dict]) -> bool:
        """Detecta palabras de frustración en los mensajes."""
        texto_completo = " ".join(str(m.get("texto", "")).lower() for m in mensajes)
        return any(kw in texto_completo for kw in self.FRUSTRACION_KEYWORDS)

    def _compute_risk_level(self, sentimiento: float, caida: float, frustacion: bool) -> float:
        """Calcula el nivel de riesgo combinando las señales."""
        riesgo = 0.0

        # Peso 1: Sentimiento negativo (40%)
        riesgo += (1 - sentimiento) * 0.4

        # Peso 2: Caída vs historial (35%)
        if caida > 0:
            riesgo += min(caida, 1) * 0.35

        # Peso 3: Frustración explícita (25%)
        if frustacion:
            riesgo += 0.25

        return min(max(riesgo, 0), 1)

    def _build_reason(self, autor, sentimiento, caida, frustacion, nivel) -> str:
        """Construye una razón legible para la alerta.

        Orden de señales por peso: frustración explícita > caída emocional
        > sentimiento bajo. Se muestran máx 2 razones para legibilidad,
        por eso las más fuertes van primero.
        """
        razones = []
        if frustacion:
            razones.append("señales de frustración en mensajes")
        if caida >= self.UMBRAL_CAIDA_EMOCIONAL:
            razones.append(f"caída emocional vs historial ({caida:.2f})")
        if sentimiento < 0.4:
            razones.append(f"sentimiento promedio bajo ({sentimiento:.2f})")

        texto = "; ".join(razones[:2])  # máx 2 razones para legibilidad
        return f"Alerta {autor}: {texto}" if razones else f"Monitoreo estándar para {autor}"