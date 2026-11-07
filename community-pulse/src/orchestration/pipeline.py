"""
Community Pulse — Pipeline principal.

Conecta: Ingest → Analysis → Decisions → Generators → OCI.
Responsable: Software Engineer
"""

import asyncio
from datetime import datetime

from src.ingest.normalizer import normalize_batch
from src.analysis.orchestrator import full_analysis
from src.orchestration.router import ContentRouter
from src.decisions.engine import DecisionEngine


class CommunityPulsePipeline:
    """Pipeline principal del sistema Community Pulse."""

    def __init__(self, llm_client, oci_storage=None, historial=None):
        self.llm = llm_client
        self.oci = oci_storage
        self.router = ContentRouter()
        self.decisions = DecisionEngine(llm_client, historial)

    async def process(self, input_data: dict) -> dict:
        """
        Procesa un lote de interacciones de la comunidad.

        Flujo:
        1. Normalizar mensajes
        2. Analizar (sentimiento + categorías + relevancia)
        3. Decisiones (riesgo, dudas recurrentes, escalamiento)
        4. Routear y generar activos
        5. Guardar en OCI (si está configurado)
        6. Retornar respuesta estructurada
        """
        # Paso 1: Normalizar
        messages = normalize_batch(
            input_data.get("interacciones", []),
            input_data.get("origen_comunidad", "discord"),
        )

        # Paso 2: Analizar en paralelo
        # full_analysis es SÍNCRONO → asyncio.to_thread para paralelismo real.
        # (asyncio.gather directo fallaría: no acepta funciones síncronas)
        analyses = await asyncio.gather(*[
            asyncio.to_thread(full_analysis, msg, self.llm) for msg in messages
        ])

        # Paso 3: Decisiones
        batch_analysis = {
            "periodo_referencia": input_data.get("periodo_referencia", "sin_periodo"),
            "mensajes_analizados": analyses,
        }
        decisiones = self.decisions.process_batch(batch_analysis)

        # Paso 4: Generar activos según decisiones
        assets = {}
        for accion in decisiones["acciones_recomendadas"]:
            if accion["tipo"] == "publicar_prioritario":
                activo = await generate_asset_for(analyses, "caso_exito", self.llm)
                assets.setdefault("casos_exito", []).append(activo)
            elif accion["tipo"] == "generar_faq":
                activo = await generate_asset_for(analyses, "faq_tip", self.llm)
                assets.setdefault("faq_tips", []).append(activo)
            elif accion["tipo"] == "alerta_sentimiento_puntual":
                pass  # las alertas van a decisions/notificaciones, no a activos

        # Paso 5: Persistir en OCI (opcional — requiere configuración)
        oci_result = None
        if self.oci:
            oci_result = self._persist_to_oci(input_data, analyses, assets, decisiones)

        # Paso 6: Respuesta
        return self._build_response(input_data, analyses, assets, decisiones, oci_result)

    def _persist_to_oci(self, input_data, analyses, assets, decisiones) -> dict:
        """Guarda el paquete completo en OCI."""
        package = {
            "periodo": input_data.get("periodo_referencia"),
            "origen": input_data.get("origen_comunidad"),
            "timestamp": datetime.now().isoformat(),
            "resumen": {
                "total_procesados": len(analyses),
                "sentimiento_predominante": self._predominant_sentiment(analyses),
            },
            "activos": assets,
            "decisiones": decisiones,
        }
        return self.oci.upload_json(
            package,
            f"activos/{input_data.get('periodo_referencia', 'sin_periodo')}/paquete-distribucion.json",
        )

    def _predominant_sentiment(self, analyses) -> str:
        from collections import Counter
        sentiments = [a["analisis"]["sentimiento"]["etiqueta"] for a in analyses]
        return Counter(sentiments).most_common(1)[0][0] if sentiments else "unknown"

    def _build_response(self, input_data, analyses, assets, decisiones, oci_result) -> dict:
        return {
            "status": "exito",
            "periodo": input_data.get("periodo_referencia"),
            "resumen_comunidad": {
                "total_interacciones_procesadas": len(analyses),
                "sentimiento_predominante": self._predominant_sentiment(analyses),
                "decisiones": decisiones,
            },
            "activos_distribucion_generados": assets,
            "almacenamiento_oci": oci_result,
        }


async def generate_asset_for(analyses, category, llm_client) -> dict:
    """Busca el análisis más relevante de la categoría y genera el activo."""
    from src.orchestration.router import ContentRouter

    router = ContentRouter()
    generators = router.get_generators(category)

    # Elegir el análisis con mayor relevancia de la categoría
    candidates = [
        a for a in analyses
        if a["analisis"]["categoria_sugerida"] == category
    ]
    if not candidates:
        candidates = analyses

    best = max(candidates, key=lambda a: a["analisis"]["relevancia_marketing"]["score"])
    gen = generators[0]
    return await gen(best, llm_client)


if __name__ == "__main__":
    import json
    import sys

    # Ejecución CLI: python -m src.orchestration.pipeline --input data.json
    filepath = sys.argv[sys.argv.index("--input") + 1] if "--input" in sys.argv else "data/sample/messages.json"
    with open(filepath) as f:
        data = json.load(f)
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
    print(f"\n⚠️ Pipeline listo. Conectá tu LLM client para ejecutar el procesamiento completo.")
