"""
CommunityLab — Endpoints REST.

Ingesta en tiempo real: POST /webhook (async, responde 202 inmediato).
Los jobs se procesan en background y se consultan con GET /jobs/{id}.

Responsable: Backend Developer
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.api.worker import JobWorker


def _build_processor():
    """
    Crea el processor del pipeline (Dependency Inversion).

    Diseño: el worker NUNCA importa el pipeline; aquí se resuelve el
    processor real. El cliente LLM se resuelve por configuración:
    - COMMUNITYLAB_LLM_BACKEND=rule_based → offline, sin API keys
    - GEMINI_API_KEY / OPENAI_API_KEY → LLM real
    """
    pipeline = None

    async def process(payload: dict) -> dict:
        nonlocal pipeline
        if pipeline is None:
            from src.orchestration.pipeline import CommunityLabPipeline
            from src.utils.llm_client import create_llm_client
            pipeline = CommunityLabPipeline(llm_client=create_llm_client())
        return await pipeline.process(payload)

    return process


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia el worker al arrancar y lo detiene al apagar."""
    app.state.worker = JobWorker(processor=_build_processor(), max_workers=3)
    await app.state.worker.start()
    yield
    await app.state.worker.stop()


app = FastAPI(title="CommunityLab API", version="0.1.0", lifespan=lifespan)


class ProcesarRequest(BaseModel):
    origen_comunidad: str
    periodo_referencia: str = "Batch_01"
    interacciones: list[dict]


@app.post("/webhook", status_code=202)
async def webhook(request: ProcesarRequest):
    """
    Recibe interacciones en tiempo real y las encola para procesar.

    Retorna 202 Accepted + job_id inmediatamente. El análisis con LLM
    ocurre en background; consultá GET /jobs/{job_id} para el resultado.
    """
    job_id = app.state.worker.submit(request.model_dump())
    return {"status": "aceptado", "job_id": job_id}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Consulta el estado y resultado de un job."""
    job = app.state.worker.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job


@app.get("/jobs")
async def list_jobs(limit: int = 20):
    """Lista los últimos jobs."""
    return {"jobs": app.state.worker.list_jobs(limit=limit)}


@app.get("/health")
async def health():
    """Health check para monitoreo."""
    return {"status": "ok", "version": "0.1.0"}