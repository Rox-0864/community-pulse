"""Tests del módulo de ingestión."""

from src.ingest.loader import load_json
from src.ingest.normalizer import normalize_batch
from src.ingest.validators import validate_batch


def test_load_json_sample():
    messages = load_json("data/sample/messages.json")
    assert len(messages) == 5
    assert all("texto" in m for m in messages)


def test_normalize_batch():
    raw = [{"autor": "Test", "canal": "#logros", "texto": "Hola mundo"}]
    normalized = normalize_batch(raw)
    assert normalized[0]["tipo"] == "logro"
    assert normalized[0]["autor"] == "Test"


def test_normalize_skips_empty():
    raw = [{"autor": "A", "texto": ""}, {"autor": "B", "texto": "Con texto"}]
    normalized = normalize_batch(raw)
    assert len(normalized) == 1


def test_validate_batch():
    valid = [{
        "id": "1",
        "autor": "A",
        "canal": "#x",
        "tipo": "general",
        "texto": "Test message",
        "timestamp": "2026-01-01",
        "origen": "discord",
    }]
    v, inv = validate_batch(valid)
    assert len(v) == 1
    assert len(inv) == 0
