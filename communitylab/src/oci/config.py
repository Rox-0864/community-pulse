"""
CommunityLab — Configuración de OCI.

NUNCA commitear credenciales reales. Usar variables de entorno.
Responsable: Backend Developer
"""

import os

OCI_CONFIG = {
    "user": os.getenv("OCI_USER_ID"),
    "key_file": os.getenv("OCI_KEY_FILE_PATH", "~/.oci/oci_api_key.pem"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION", "sa-saopaulo-1"),
    "compartment_id": os.getenv("OCI_COMPARTMENT_ID"),
}

OCI_BUCKET_NAME = os.getenv("OCI_BUCKET_NAME", "communitylab-activos-marketing")


def has_oci_credentials() -> bool:
    """Verifica si hay credenciales OCI configuradas."""
    return all([OCI_CONFIG["user"], OCI_CONFIG["tenancy"], OCI_CONFIG["fingerprint"]])
