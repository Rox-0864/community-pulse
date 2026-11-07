"""Configuración compartida de tests."""

import json
import sys
from pathlib import Path

import pytest

# Agregar raíz del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ----------------------------------------------------------------------
# Fake LLM client (funciona en llamadas sync y async)
# ----------------------------------------------------------------------
class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class FakeLLMResponse:
    """Respuesta con __await__ para soportar llamadas sync y async."""

    def __init__(self, payload: dict):
        self.choices = [_FakeChoice(json.dumps(payload, ensure_ascii=False))]

    def __await__(self):
        async def _wrap():
            return self
        return _wrap().__await__()


class FakeLLMClient:
    """Cliente LLM falso que devuelve payloads en orden (el último se repite).

    - ``FakeLLMClient({"a": 1})`` → siempre devuelve ese payload.
    - ``FakeLLMClient([p1, p2, p3])`` → consume uno por llamada, repite el último.
    """

    def __init__(self, payloads):
        if isinstance(payloads, dict):
            payloads = [payloads]
        self._payloads = list(payloads)
        self.calls = []
        self.chat = _FakeChat(self)

    def _pop(self):
        if not self._payloads:
            return {}
        if len(self._payloads) == 1:
            return self._payloads[0]
        return self._payloads.pop(0)


class _FakeCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, model, messages, response_format=None):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        self._client.calls.append({"system": system, "user": user})
        return FakeLLMResponse(self._client._pop())


class _FakeChat:
    def __init__(self, client):
        self.completions = _FakeCompletions(client)


@pytest.fixture
def fake_llm():
    """Factory: ``fake_llm(payload)`` o ``fake_llm([p1, p2, ...])``."""
    def _make(payloads):
        return FakeLLMClient(payloads)
    return _make
