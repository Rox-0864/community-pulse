"""Tests del cliente real de OCI (src/oci/client.py).

Verifican el puente desde config.py hacia el SDK real de OCI:
- factory que devuelve None sin credenciales
- construcción del ObjectStorageClient + namespace + bucket
- config desde env vars vs fallback al archivo ~/.oci/config
- mensaje de error claro si no está instalado el SDK
"""

import importlib.util

import pytest

from src.oci import config
from src.oci.client import OCIClient, _build_oci_config, _import_oci, create_oci_storage
from src.oci.storage import OCIStorage


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _fake_oci(namespace="ns_demo"):
    """SDK de OCI falso: ObjectStorageClient + config.from_file."""

    class _FakeObjectStorageClient:
        def __init__(self, cfg):
            self.config = cfg

        def get_namespace(self):
            class _Resp:
                data = namespace
            return _Resp()

    class _ObjectStorage:
        ObjectStorageClient = _FakeObjectStorageClient

    class _Config:
        @staticmethod
        def from_file(profile_name=None):
            return {"__from_file__": True}

    class _FakeOCI:
        object_storage = _ObjectStorage()
        config = _Config()

    return _FakeOCI


def _set_credentials(monkeypatch):
    monkeypatch.setitem(config.OCI_CONFIG, "user", "u")
    monkeypatch.setitem(config.OCI_CONFIG, "tenancy", "t")
    monkeypatch.setitem(config.OCI_CONFIG, "fingerprint", "f")


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def test_create_oci_storage_sin_credenciales_retorna_none():
    """Sin credenciales OCI, el pipeline persiste NADA (None)."""
    assert create_oci_storage() is None


def test_create_oci_storage_con_credenciales(monkeypatch):
    _set_credentials(monkeypatch)
    monkeypatch.setattr("src.oci.client._import_oci", lambda: _fake_oci())

    storage = create_oci_storage()

    assert isinstance(storage, OCIStorage)
    assert isinstance(storage.client, OCIClient)
    assert storage.client.namespace == "ns_demo"
    assert storage.client.bucket_name == "community-pulse-activos-marketing"


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
def test_build_config_desde_env(monkeypatch):
    _set_credentials(monkeypatch)
    monkeypatch.setitem(config.OCI_CONFIG, "key_file", "/tmp/key.pem")
    monkeypatch.setitem(config.OCI_CONFIG, "region", "sa-saopaulo-1")

    cfg = _build_oci_config()

    assert cfg["user"] == "u"
    assert cfg["tenancy"] == "t"
    assert cfg["fingerprint"] == "f"
    assert cfg["key_file"] == "/tmp/key.pem"
    assert cfg["region"] == "sa-saopaulo-1"


def test_build_config_fallback_al_archivo(monkeypatch):
    """Sin credenciales explícitas, cae al ~/.oci/config estándar."""
    fake = _fake_oci()
    monkeypatch.setattr("src.oci.client._import_oci", lambda: fake)

    cfg = _build_oci_config()

    assert cfg == {"__from_file__": True}


# ----------------------------------------------------------------------
# OCIClient
# ----------------------------------------------------------------------
def test_oci_client_construye_sdk_y_resuelve_namespace(monkeypatch):
    _set_credentials(monkeypatch)
    fake = _fake_oci(namespace="mi_namespace")
    monkeypatch.setattr("src.oci.client._import_oci", lambda: fake)

    client = OCIClient(bucket_name="bucket_custom")

    assert client.namespace == "mi_namespace"
    assert client.bucket_name == "bucket_custom"
    # El SDK client recibió la config construida desde env
    assert client.object_storage_client.config["user"] == "u"


# ----------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------
def test_import_error_sugiere_pip_install():
    if importlib.util.find_spec("oci") is not None:
        pytest.skip("oci instalado; este test no aplica")
    with pytest.raises(ImportError, match="pip install oci"):
        _import_oci()
