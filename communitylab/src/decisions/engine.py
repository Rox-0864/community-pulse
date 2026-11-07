"""
CommunityLab — Motor principal de decisiones.

Recibe el análisis de todos los mensajes del lote y decide qué acciones
ejecutar basándose en reglas + señales del LLM.

⚠️ IMPORTANTE (formato de entrada tolerante):
- La espec (modulo_toma_decisiones.md) asume formato plano:
    msg["categoria_sugerida"], msg["relevancia"], msg["sentimiento"]
- PERO full_analysis() del orchestrator retorna formato ANIDADO:
    msg["analisis"]["categoria_sugerida"], msg["analisis"]["relevancia_marketing"],
    msg["analisis"]["sentimiento"]
- Este engine lee AMBOS formatos vía _get(msg, campo).

Responsables: Software Engineer + Data Scientists
"""

from collections import Counter
from datetime import datetime
from typing import Optional

from src.decisions.member_risk import MemberRiskDetector
from src.decisions.recurring_topics import RecurringTopicsDetector
from src.decisions.escalation import EscalationRules
from src.decisions.notifications import NotificationBuilder


class DecisionEngine:
    """Motor principal de decisiones de CommunityLab."""

    def __init__(self, llm_client, historial: dict = None):
        self.llm = llm_client
        self.historial = historial or {
            "mensajes_semanas_previas": [],
            "dudas_resueltas": [],
            "miembros_tracking": {}
        }
        self.risk_detector = MemberRiskDetector(llm_client, self.historial)
        self.recurring_detector = RecurringTopicsDetector()
        self.escalation = EscalationRules()
        self.notifications = NotificationBuilder()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def process_batch(self, batch_analysis: dict) -> dict:
        """
        Procesa un lote de mensajes analizados y decide acciones.

        Flujo de decisión para cada mensaje:
        1. ¿Es un testimonio de alto valor? → publicar prioritario
        2. ¿Es una duda técnica? → FAQ
        3. ¿El autor tiene sentimiento negativo? → alerta puntual
        4. ¿Dudas recurrentes vs historial? → derivar a mentoría
        5. ¿Riesgo de abandono por autor? → alerta miembro
        """
        acciones = []
        autores_en_batch = {}

        # Agrupar mensajes por autor para análisis de riesgo
        for msg in batch_analysis.get("mensajes_analizados", []):
            autor = msg.get("autor", "anónimo")
            autores_en_batch.setdefault(autor, []).append(msg)

        # Decisión por mensaje
        for msg in batch_analysis.get("mensajes_analizados", []):
            accion = self._decidir_por_mensaje(msg)
            if accion:
                acciones.append(accion)

        # Detección de dudas recurrentes (buscar en historial)
        dudas = self.recurring_detector.detect(
            batch_analysis.get("mensajes_analizados", []),
            self.historial.get("dudas_resueltas", [])
        )
        for duda in dudas:
            acciones.append({
                "tipo": "derivar_mentoria",
                "tema": duda["tema"],
                "veces_detectada": duda["veces_detectada"],
                "mentor_sugerido": duda["mentor_sugerido"],
                "activo_sugerido": "faq_tip"
            })

        # Análisis de riesgo por autor (requiere historial)
        for autor, mensajes_autor in autores_en_batch.items():
            riesgo = self.risk_detector.evaluate_author(autor, mensajes_autor)
            # Umbral INCLUSIVO (>=): el detector ya decide "contactar_individualmente"
            # con riesgo >= UMBRAL_ALERTA; si el engine usara ">" estricto, un
            # riesgo exactamente en el umbral (e.g. 0.60) sería silenciado.
            if riesgo["nivel_riesgo"] >= MemberRiskDetector.UMBRAL_ALERTA:
                acciones.append({
                    "tipo": "alerta_miembro",
                    "autor": autor,
                    "nivel_riesgo": riesgo["nivel_riesgo"],
                    "razon": riesgo["razon"],
                    "accion_sugerida": riesgo["accion_sugerida"],
                    "senales": riesgo["senales"],  # requerido por build_member_alert
                })

        # Construir resumen ejecutivo
        resumen = self._build_resumen(acciones)

        return {
            "acciones_recomendadas": acciones,
            "resumen_ejecutivo": resumen
        }

    def build_notifications(self, decisiones: dict) -> list[dict]:
        """Convierte las decisiones en notificaciones para el dashboard."""
        notificaciones = []
        for accion in decisiones.get("acciones_recomendadas", []):
            escalamiento = self.escalation.classify(accion)
            tipo = accion["tipo"]

            if tipo == "alerta_miembro":
                notificaciones.append(
                    self.notifications.build_member_alert(accion, escalamiento)
                )
            elif tipo == "derivar_mentoria":
                notificaciones.append(
                    self.notifications.build_mentorship_referral(accion, escalamiento)
                )
            elif tipo == "publicar_prioritario":
                notificaciones.append(
                    self.notifications.build_publication_priority(accion)
                )
            # alertas puntuales de sentimiento → se registran en dashboard
            else:
                notificaciones.append({
                    "tipo_notificacion": tipo.upper(),
                    "gravedad": escalamiento["nivel"],
                    "titulo": f"📌 Acción: {tipo}",
                    "mensaje": accion.get("razon", ""),
                    "timestamp": datetime.now().isoformat(),
                    "destinatario": "dashboard",
                    "canal": "dashboard"
                })
        return notificaciones

    # ------------------------------------------------------------------
    # Lógica de decisión
    # ------------------------------------------------------------------
    def _decidir_por_mensaje(self, msg: dict) -> Optional[dict]:
        """Reglas de decisión para un mensaje individual."""
        categoria = self._get(msg, "categoria_sugerida")

        # R1: Testimonio de alto valor → publicar prioritario
        if categoria == "caso_exito" and self._get(msg, "relevancia", 0) > 0.8:
            return {
                "tipo": "publicar_prioritario",
                "mensaje_id": msg.get("id"),
                "razon": f"Testimonio con relevancia {self._get(msg, 'relevancia', 0):.2f}",
                "prioridad": "ALTA",
                "activo_sugerido": "post_linkedin"
            }

        # R2: Duda técnica → FAQ (se combina con detección recurrente)
        if categoria == "faq_tip":
            return {
                "tipo": "generar_faq",
                "mensaje_id": msg.get("id"),
                "razon": "Duda técnica identificada",
                "activo_sugerido": "faq_tip"
            }

        # R3: Sentimiento negativo fuerte → alerta de riesgo
        sentimiento = self._get(msg, "sentimiento", {}) or {}
        if sentimiento.get("etiqueta") in ["negativo", "muy_negativo"]:
            return {
                "tipo": "alerta_sentimiento_puntual",
                "mensaje_id": msg.get("id"),
                "razon": f"Sentimiento {sentimiento.get('etiqueta')} detectado",
                "accion_sugerida": "monitorear"
            }

        return None

    def _build_resumen(self, acciones: list[dict]) -> dict:
        """Construye el resumen ejecutivo para el dashboard."""
        tipos = Counter(a["tipo"] for a in acciones)
        return {
            "miembros_en_riesgo": tipos.get("alerta_miembro", 0) + tipos.get("alerta_sentimiento_puntual", 0),
            "dudas_detectadas": tipos.get("generar_faq", 0) + tipos.get("derivar_mentoria", 0),
            "testimonios_destacables": tipos.get("publicar_prioritario", 0),
            "acciones_automaticas": len(acciones)
        }

    # ------------------------------------------------------------------
    # Helper: leer campo tolerando formato plano y anidado
    # ------------------------------------------------------------------
    def _get(self, msg: dict, campo: str, default=None):
        """
        Lee un campo que puede estar en la raíz del mensaje (spec) o
        bajo msg["analisis"] (orchestrator).

        Mapeos equivalentes:
            categoria_sugerida → analisis.categoria_sugerida
            relevancia        → analisis.relevancia_marketing.score
            sentimiento       → analisis.sentimiento
            temas             → analisis.temas
        """
        if campo in msg and msg[campo] is not None:
            return msg[campo]

        analisis = msg.get("analisis") or {}

        # Mapeo de nombres entre spec y orchestrator
        if campo == "relevancia":
            rel = analisis.get("relevancia_marketing")
            if isinstance(rel, dict):
                return rel.get("score", default)
            return analisis.get("relevancia", default)

        if campo in analisis:
            return analisis[campo]

        return default