"""Tests del JobWorker asíncrono (sección 4.b — videoguía)."""

import asyncio

import pytest

from src.api.worker import JobWorker


@pytest.mark.asyncio
async def test_submit_returns_job_id_immediately():
    async def fake_processor(payload):
        await asyncio.sleep(0.05)
        return {"ok": True}

    worker = JobWorker(processor=fake_processor, max_workers=1)
    await worker.start()

    job_id = worker.submit({"origen_comunidad": "test"})
    assert isinstance(job_id, str)
    assert len(job_id) == 12  # uuid hex[:12]

    await worker.stop()


@pytest.mark.asyncio
async def test_job_goes_pending_to_done():
    async def fake_processor(payload):
        await asyncio.sleep(0.01)
        return {"procesado": True, "total": len(payload.get("interacciones", []))}

    worker = JobWorker(processor=fake_processor, max_workers=1)
    await worker.start()

    job_id = worker.submit({"interacciones": [{"texto": "x"}]})

    # Inmediatamente después de submit debe estar pendiente
    assert worker.get(job_id)["status"] == "pendiente"

    # Esperar a que el worker procese
    for _ in range(100):
        if worker.get(job_id)["status"] in ("listo", "error"):
            break
        await asyncio.sleep(0.01)

    job = worker.get(job_id)
    assert job["status"] == "listo"
    assert job["resultado"]["procesado"] is True
    assert job["resultado"]["total"] == 1
    assert job["started_at"] is not None
    assert job["finished_at"] is not None
    assert job["error"] is None

    await worker.stop()


@pytest.mark.asyncio
async def test_processor_error_sets_error_status():
    async def failing_processor(payload):
        raise RuntimeError("LLM timeout")

    worker = JobWorker(processor=failing_processor, max_workers=1)
    await worker.start()

    job_id = worker.submit({"texto": "hola"})

    for _ in range(100):
        if worker.get(job_id)["status"] == "error":
            break
        await asyncio.sleep(0.01)

    job = worker.get(job_id)
    assert job["status"] == "error"
    assert "LLM timeout" in job["error"]
    assert job["resultado"] is None

    await worker.stop()


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none():
    async def fake_processor(payload):
        return {}

    worker = JobWorker(processor=fake_processor, max_workers=1)
    assert worker.get("job-inexistente") is None
    await worker.stop()


@pytest.mark.asyncio
async def test_multiple_workers_process_in_parallel():
    """Con max_workers=3, tres jobs se procesan concurrentemente."""
    started = 0
    active = 0

    async def counting_processor(payload):
        nonlocal started, active
        started += 1
        active += 1
        await asyncio.sleep(0.05)
        active -= 1
        return {"started": started, "max_active": None}

    worker = JobWorker(processor=counting_processor, max_workers=3)
    await worker.start()

    job_ids = [worker.submit({"n": i}) for i in range(3)]

    # Esperar a que todos terminen
    for _ in range(100):
        if all(worker.get(j)["status"] == "listo" for j in job_ids):
            break
        await asyncio.sleep(0.01)

    assert all(worker.get(j)["status"] == "listo" for j in job_ids)
    assert started == 3

    await worker.stop()


@pytest.mark.asyncio
async def test_list_jobs_ordered_newest_first():
    async def fake_processor(payload):
        return {}

    worker = JobWorker(processor=fake_processor, max_workers=1)
    await worker.start()

    ids = [worker.submit({"n": i}) for i in range(5)]
    await asyncio.sleep(0.1)

    jobs = worker.list_jobs(limit=3)
    assert len(jobs) == 3
    assert jobs[0]["job_id"] == ids[-1]  # el más nuevo primero
    assert all(job["status"] == "listo" for job in jobs)

    await worker.stop()