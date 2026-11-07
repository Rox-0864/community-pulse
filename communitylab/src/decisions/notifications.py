"""
CommunityLab — Genera las alertas/notificaciones.

Convierte las decisiones en notificaciones accionables para el community manager.
Responsable: Software Engineer + Backend Developer
"""

from datetime import datetime


class NotificationBuilder:
    """Construye notificaciones legibles para humanos."""

    def build_member_alert(self, alerta: dict, escalamiento: dict) -> dict:
        """Notificación para miembro en riesgo."""
        return {
            "tipo_notificacion": "ALERTA_MIEMBRO",
            "gravedad": escalamiento["nivel"],
            "titulo": f"⚠️ Miembro en riesgo: {alerta['autor']}",
            "mensaje": f"""Miembro {alerta['autor']} muestra señales de posible abandono.

Razón: {alerta['razon']}
Nivel de riesgo: {alerta['nivel_riesgo']:.0%}
Señales detectadas:
• Sentimiento reciente: {alerta['senales']['sentimiento_reciente']}
• Caída vs historial: {alerta['senales']['caida_vs_historial']}
• Frustración en mensajes: {'Sí' if alerta['senales']['frustracion_detectada'] else 'No'}

Acción requerida: {alerta['accion_sugerida']}
Tiempo de respuesta: {escalamiento['tiempo_respuesta']}""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": "community_manager",
            "canal": "dashboard"
        }

    def build_mentorship_referral(self, duda: dict, escalamiento: dict) -> dict:
        """Notificación para derivación a mentoría."""
        return {
            "tipo_notificacion": "DERIVAR_MENTORIA",
            "gravedad": escalamiento["nivel"],
            "titulo": f"📚 Duda recurrente: {duda['tema']}",
            "mensaje": f"""La siguiente duda apareció {duda['veces_detectada']} veces en la comunidad:
"{duda['tema']}"

Mentor sugerido: {duda['mentor_sugerido']}
Acción: {duda.get('accion', 'generar_faq_y_derivar')}

Se generó FAQ automático. Se sugiere revisión de mentor.""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": duda["mentor_sugerido"],
            "canal": "dashboard"
        }

    def build_publication_priority(self, testimonio: dict) -> dict:
        """Notificación para publicación prioritaria."""
        return {
            "tipo_notificacion": "PUBLICAR_PRIORITARIO",
            "gravedad": "INFO",
            "titulo": "🚀 Testimonio listo para publicación",
            "mensaje": f"""Un testimonio de alto valor está listo para publicar.

Razón: {testimonio['razon']}
Activo generado: {testimonio.get('activo_sugerido', 'post_linkedin')}
Canal recomendado: LinkedIn Oficial

Aprobación requerida en panel de curaduría.""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": "equipo_marketing",
            "canal": "dashboard"
        }