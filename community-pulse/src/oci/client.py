"""
Community Pulse — Cliente real de OCI Object Storage.

Puente entre ``config.py`` (variables de entorno) y el SDK oficial de
Oracle Cloud Infrastructure. Expone el ``object_storage_client``, el
``namespace`` resuelto y el ``bucket_name`` que consume ``OCIStorage``.

Modos de configuración:
1. Variables de entorno completas (``OCI_USER_ID``, ``OCI_TENANCY_ID``,
   ``OCI_FINGERPRINT``) → se construye el config dict a mano.
2. Sin env vars → se usa el archivo estándar ``~/.oci/config`` del SDK.

Responsable: Backend Developer
"""

from src.oci import config as oci_config
from src.oci.storage import OCIStorage


class OCIClient:
    """Envuelve ObjectStorageClient + namespace + bucket.

    Atributos (los que espera ``OCIStorage``):
        object_storage_client: cliente del SDK de Object Storage.
        namespace:            namespace del tenancy (get_namespace).
        bucket_name:          bucket destino de los activos.
    """

    def __init__(self, config: dict = None, bucket_name: str = None):
        config = config if config is not None else _build_oci_config()
        self.object_storage_client = _import_oci().object_storage.ObjectStorageClient(config)
        self.namespace = self.object_storage_client.get_namespace().data
        self.bucket_name = bucket_name or oci_config.OCI_BUCKET_NAME


def _build_oci_config() -> dict:
    """Config OCI: env vars explícitas o archivo ~/.oci/config estándar."""
    if oci_config.has_oci_credentials():
        return {
            "user": oci_config.OCI_CONFIG["user"],
            "key_file": oci_config.OCI_CONFIG["key_file"],
            "fingerprint": oci_config.OCI_CONFIG["fingerprint"],
            "tenancy": oci_config.OCI_CONFIG["tenancy"],
            "region": oci_config.OCI_CONFIG["region"],
        }
    return _import_oci().config.from_file()


def _import_oci():
    """Importa el SDK de OCI (lazy) con un mensaje de error claro."""
    try:
        import oci
        return oci
    except ImportError as e:
        raise ImportError("Instala el SDK de OCI: pip install oci") from e


def create_oci_storage():
    """
    Crea el ``OCIStorage`` real si hay credenciales OCI configuradas.

    Retorna ``None`` si no hay credenciales (el pipeline persiste NADA).
    Si las credenciales están configuradas pero son inválidas, deja que
    el error se propague para no ocultar una mala configuración.
    """
    if not oci_config.has_oci_credentials():
        return None
    return OCIStorage(OCIClient())
