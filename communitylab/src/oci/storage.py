"""
Community Pulse — Almacenamiento en OCI Object Storage.

Responsable: Backend Developer
"""

import json
from datetime import datetime


class OCIStorage:
    """Funciones de almacenamiento en OCI."""

    def __init__(self, client):
        self.client = client

    def upload_json(self, data: dict, path: str) -> dict:
        """
        Sube un archivo JSON a OCI.

        Args:
            data: Datos a guardar
            path: Ruta en el bucket (ej: "activos/2026-semana-04/paquete.json")

        Returns:
            dict con status y detalles
        """
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        response = self.client.object_storage_client.put_object(
            namespace_name=self.client.namespace,
            bucket_name=self.client.bucket_name,
            object_name=path,
            put_object_body=json_bytes,
            content_type="application/json",
        )

        return {
            "status": "guardado_con_exito" if response.status == 200 else "error",
            "bucket": self.client.bucket_name,
            "ruta_objeto": path,
            "tamano_bytes": len(json_bytes),
        }

    def generate_path(self, periodo: str, tipo: str = "paquete") -> str:
        """Genera la ruta del objeto basada en el período."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"activos/{periodo}/{tipo}-{timestamp}.json"
