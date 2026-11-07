"""
CommunityLab — Reglas de escalamiento.

Clasifica la gravedad de las alertas y define la acción a tomar.
Responsable: Software Engineer
"""


class EscalationRules:
    """Reglas para escalar alertas según su gravedad."""

    NIVELES_ESCALAMIENTO = {
        "INFO": {
            "prioridad": 1,
            "tiempo_respuesta": "24 horas",
            "accion": "registrar_en_dashboard"
        },
        "MEDIO": {
            "prioridad": 2,
            "tiempo_respuesta": "4 horas",
            "accion": "notificar_community_manager"
        },
        "ALTO": {
            "prioridad": 3,
            "tiempo_respuesta": "1 hora",
            "accion": "notificar_team_lead + contactar_miembro"
        },
        "CRITICO": {
            "prioridad": 4,
            "tiempo_respuesta": "inmediato",
            "accion": "contacto_personal + revisión de caso + plan de retención"
        }
    }

    def classify(self, alerta: dict) -> dict:
        """
        Clasifica la gravedad de una alerta.

        Criterios:
        - nivel_riesgo > 0.85 o frustración + abandono → CRITICO
        - nivel_riesgo > 0.6 o queja de curso/feature → ALTO
        - nivel_riesgo > 0.4 o duda recurrente ≥5 → MEDIO
        - resto → INFO
        """
        nivel_riesgo = alerta.get("nivel_riesgo", 0)
        tipo = alerta.get("tipo", "")
        tema = alerta.get("tema", "").lower()

        # Criterios CRITICO
        if nivel_riesgo > 0.85:
            nivel = "CRITICO"
        elif nivel_riesgo > 0.6 or "queja" in tipo:
            nivel = "ALTO"
        elif nivel_riesgo > 0.4 or alerta.get("veces_detectada", 0) >= 5:
            nivel = "MEDIO"
        else:
            nivel = "INFO"

        reglas = self.NIVELES_ESCALAMIENTO[nivel]

        return {
            "nivel": nivel,
            "prioridad": reglas["prioridad"],
            "tiempo_respuesta": reglas["tiempo_respuesta"],
            "accion": reglas["accion"],
            "requiere_intervencion_humana": nivel in ["ALTO", "CRITICO"]
        }