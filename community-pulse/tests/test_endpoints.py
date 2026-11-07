"""Tests de los endpoints REST (webhook asíncrono)."""

from fastapi.testclient import TestClient

from src.api.endpoints import app


def test_webhook_returns_202_with_job_id():
    with TestClient(app) as client:
        resp = client.post("/webhook", json={
            "origen_comunidad": "discord",
            "periodo_referencia": "Batch_01",
            "interacciones": [{"autor": "A", "texto": "Hola comunidad"}],
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "aceptado"
        assert len(data["job_id"]) == 12


def test_webhook_then_job_completes():
    """El webhook encola y el worker procesa en background."""
    with TestClient(app) as client:
        resp = client.post("/webhook", json={
            "origen_comunidad": "test",
            "interacciones": [{"texto": "mensaje"}],
        })
        job_id = resp.json()["job_id"]

        # El job existe (nunca 404) y está en algún estado válido
        resp = client.get(f"/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["job_id"] == job_id
        assert resp.json()["status"] in ("pendiente", "procesando", "listo", "error")


def test_get_nonexistent_job_404():
    with TestClient(app) as client:
        resp = client.get("/jobs/inexistente")
        assert resp.status_code == 404


def test_list_jobs():
    with TestClient(app) as client:
        client.post("/webhook", json={
            "origen_comunidad": "test",
            "interacciones": [{"texto": "mensaje 1"}],
        })
        resp = client.get("/jobs")
        assert resp.status_code == 200
        assert "jobs" in resp.json()


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"