"""
Community Pulse — Job Worker asíncrono con asyncio.Queue.

Patrón: accept → queue → process → result (nunca bloquea al cliente).
Processor se inyecta, NO importa el pipeline directamente (Dependency Inversion).

Responsable: Backend Developer
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional


class JobWorker:
    """Worker que consume interacciones de una cola y las procesa en background.

    Estados de un job:
        pendiente  → procesando → listo
                     procesando → error
    """

    def __init__(
        self,
        processor: Callable[[dict], Awaitable[dict]],
        max_workers: int = 3,
    ):
        self._processor = processor
        self._max_workers = max_workers
        self._queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()
        self._jobs: dict[str, dict] = {}
        self._tasks: list[asyncio.Task] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self):
        """Lanza los workers que consumen la cola."""
        self._tasks = [
            asyncio.create_task(self._run_worker(i), name=f"cw-worker-{i}")
            for i in range(self._max_workers)
        ]

    async def stop(self, timeout: float = 5.0):
        """Cancela todos los workers y espera a que terminen."""
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)

    # ------------------------------------------------------------------
    # API pública (síncrona — segura para llamar desde endpoints)
    # ------------------------------------------------------------------
    def submit(self, payload: dict) -> str:
        """Encola un job y retorna el job_id inmediatamente."""
        job_id = uuid.uuid4().hex[:12]
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "pendiente",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "finished_at": None,
            "resultado": None,
            "error": None,
        }
        self._queue.put_nowait((job_id, payload))
        return job_id

    def get(self, job_id: str) -> Optional[dict]:
        """Retorna el estado de un job o None si no existe."""
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[dict]:
        """Retorna los últimos N jobs ordenados por fecha de creación."""
        jobs = sorted(self._jobs.values(), key=lambda j: j["created_at"], reverse=True)
        return jobs[:limit]

    # ------------------------------------------------------------------
    # Worker loop (interno)
    # ------------------------------------------------------------------
    async def _run_worker(self, worker_id: int):
        """Loop infinito que consume jobs de la cola."""
        while True:
            job_id, payload = await self._queue.get()
            try:
                self._jobs[job_id]["status"] = "procesando"
                self._jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

                resultado = await self._processor(payload)

                self._jobs[job_id]["status"] = "listo"
                self._jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                self._jobs[job_id]["resultado"] = resultado

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._jobs[job_id]["status"] = "error"
                self._jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
                self._jobs[job_id]["error"] = str(exc)
            finally:
                self._queue.task_done()
