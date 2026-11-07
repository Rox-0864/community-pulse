"""
CommunityLab — Router condicional.

Decide qué generadores ejecutar según la categoría del mensaje.
Responsable: Software Engineer
"""

from src.generators import generate_linkedin_post, generate_newsletter, generate_faq_tip, generate_testimonial


class ContentRouter:
    """Decide qué generar según la categoría del mensaje."""

    ROUTE_MAP = {
        "caso_exito": [generate_linkedin_post, generate_testimonial],
        "faq_tip": [generate_faq_tip, generate_newsletter],
        "newsletter_highlight": [generate_newsletter],
        "alerta_sentimiento": [],
    }

    def get_generators(self, category: str) -> list:
        """Retorna la lista de generadores para una categoría."""
        generators = self.ROUTE_MAP.get(category, [])
        if not generators:
            return [generate_newsletter]
        return generators
