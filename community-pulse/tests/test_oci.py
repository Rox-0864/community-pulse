"""Tests de OCI: storage.py y config.py."""

from unittest.mock import Mock

from src.oci.storage import OCIStorage
from src.oci import config


# ----------------------------------------------------------------------
# OCIStorage
# ----------------------------------------------------------------------
def test_upload_json_exito():
    client = Mock()
    client.namespace = "ns_demo"
    client.bucket_name = "bucket_demo"
    client.object_storage_client.put_object.return_value.status = 200

    storage = OCIStorage(client)
    result = storage.upload_json(
        {"nombre": "Ana"}, "activos/semana/paquete.json"
    )

    assert result["status"] == "guardado_con_exito"
    assert result["bucket"] == "bucket_demo"
    assert result["ruta_objeto"] == "activos/semana/paquete.json"
    assert result["tamano_bytes"] > 0

    client.object_storage_client.put_object.assert_called_once()
    kwargs = client.object_storage_client.put_object.call_args.kwargs
    assert kwargs["namespace_name"] == "ns_demo"
    assert kwargs["bucket_name"] == "bucket_demo"
    assert kwargs["object_name"] == "activos/semana/paquete.json"
    assert kwargs["content_type"] == "application/json"


def test_upload_json_error_status():
    client = Mock()
    client.object_storage_client.put_object.return_value.status = 500

    storage = OCIStorage(client)
    result = storage.upload_json({}, "x.json")

    assert result["status"] == "error"


def test_upload_json_serializa_utf8_sin_escapar():
    client = Mock()
    client.object_storage_client.put_object.return_value.status = 200

    storage = OCIStorage(client)
    storage.upload_json({"emoji": "🚀", "acento": "canción"}, "x.json")

    body = client.object_storage_client.put_object.call_args.kwargs["put_object_body"]
    decodificado = body.decode("utf-8")
    assert "🚀" in decodificado
    assert "canción" in decodificado


def test_generate_path():
    storage = OCIStorage(Mock())
    path = storage.generate_path("2026-semana-04")

    assert path.startswith("activos/2026-semana-04/")
    assert path.endswith(".json")
    assert "paquete" in path


def test_generate_path_con_tipo():
    storage = OCIStorage(Mock())
    path = storage.generate_path("2026-semana-04", tipo="caso_exito")

    assert path.startswith("activos/2026-semana-04/caso_exito-")


# ----------------------------------------------------------------------
# config
# ----------------------------------------------------------------------
def test_has_oci_credentials_completo(monkeypatch):
    monkeypatch.setitem(config.OCI_CONFIG, "user", "u")
    monkeypatch.setitem(config.OCI_CONFIG, "tenancy", "t")
    monkeypatch.setitem(config.OCI_CONFIG, "fingerprint", "f")
    assert config.has_oci_credentials() is True


def test_has_oci_credentials_incompleto(monkeypatch):
    monkeypatch.setitem(config.OCI_CONFIG, "user", None)
    monkeypatch.setitem(config.OCI_CONFIG, "tenancy", "t")
    monkeypatch.setitem(config.OCI_CONFIG, "fingerprint", "f")
    assert config.has_oci_credentials() is False


def test_config_defaults():
    assert config.OCI_BUCKET_NAME == "community-pulse-activos-marketing"
    assert config.OCI_CONFIG["region"] == "sa-saopaulo-1"
