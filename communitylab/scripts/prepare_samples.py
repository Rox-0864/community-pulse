"""
CommunityLab — Prepara el dataset combinado listo para el pipeline.

Uso:
    python scripts/prepare_samples.py                # Convierte data/real/*.json
    python scripts/prepare_samples.py --half          # Reduce cada fuente a la mitad
    python scripts/prepare_samples.py --mini          # Solo 50 interacciones por fuente (demo)

Este script:
    1. Lee todos los archivos de data/real/*.json
    2. Los combina en data/processed/dataset_combinado.json
    3. Genera data/processed/resumen_datos.json con estadísticas por fuente
    4. El resultado cumple el contrato del pipeline:
       {origen_comunidad, periodo_referencia, interacciones: [...]}
"""

import argparse
import json
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
REAL_DIR = BASE_DIR / "data" / "real"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

CANALES_VALIDOS = {"#general", "#dudas", "#logros", "#feedback", "r/"}
TIPOS_VALIDOS = {"general", "pregunta_tecnica", "logro", "feedback", "testimonio"}


def limpiar_interaccion(interaccion: dict, origen: str) -> dict:
    """Normaliza una interacción al contrato mínimo del pipeline."""
    texto = str(interaccion.get("texto", "")).strip()

    # Compatibilidad con el schema de validación real (MessageSchema: min_length=10)
    if len(texto) < 10:
        return None
    texto = texto[:1000]

    canal = str(interaccion.get("canal", "#general"))
    # Mapear canales fuera del esquema a #general
    if canal not in CANALES_VALIDOS and not canal.startswith("r/"):
        canal = "#general"

    tipo = str(interaccion.get("tipo", "general"))
    if tipo not in TIPOS_VALIDOS:
        tipo = "general"

    return {
        "id": f"{origen}_{abs(hash(texto)) % 1000000:06d}",
        "autor": str(interaccion.get("autor", "anonimo"))[:80],
        "canal": canal,
        "tipo": tipo,
        "texto": texto[:1000],
        "timestamp": str(interaccion.get("timestamp", "2025-01-01T00:00:00Z"))[:30],
        "metadata": interaccion.get("metadata", {}),
        "origen": origen,
    }


def main():
    parser = argparse.ArgumentParser(description="Prepara dataset combinado de CommunityLab")
    parser.add_argument("--half", action="store_true", help="Reduce cada fuente a la mitad")
    parser.add_argument("--mini", action="store_true", help="Solo 50 por fuente (demo rápida)")
    args = parser.parse_args()

    if not REAL_DIR.exists():
        raise SystemExit("❌ Ejecuta primero: python scripts/download_datasets.py --all")

    archivos = sorted(REAL_DIR.glob("*.json"))
    if not archivos:
        raise SystemExit(f"❌ No hay archivos en {REAL_DIR}. Ejecuta download_datasets.py primero.")

    dataset, stats = [], {}
    for archivo in archivos:
        origen = archivo.stem
        with open(archivo, "r", encoding="utf-8") as f:
            paquete = json.load(f)

        interacciones = paquete.get("interacciones", [])

        # Limitar tamaño si se pide
        limite = 50 if args.mini else (len(interacciones) // 2 if args.half else None)
        if limite is not None:
            interacciones = interacciones[:limite]

        for interaccion in interacciones:
            limpia = limpiar_interaccion(interaccion, origen)
            if limpia is not None:
                dataset.append(limpia)

        stats[origen] = {
            "total_crudo": len(paquete.get("interacciones", [])),
            "usadas": sum(1 for i in dataset if i["origen"] == origen),
        }

    # Dataset combinado en formato del pipeline
    salida = {
        "origen_comunidad": "comunidad_combinada",
        "periodo_referencia": "Batch_01",
        "interacciones": dataset,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    destino = PROCESSED_DIR / "dataset_combinado.json"
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    resumen = {
        "total_interacciones": len(dataset),
        "por_fuente": stats,
        "distribucion_canales": dict(Counter(i["canal"] for i in dataset)),
        "distribucion_tipos": dict(Counter(i["tipo"] for i in dataset)),
        "autores_unicos": len(set(i["autor"] for i in dataset)),
    }
    with open(PROCESSED_DIR / "resumen_datos.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(f"✅ Dataset combinado: {destino}")
    print(f"✅ Resumen: {PROCESSED_DIR / 'resumen_datos.json'}")
    print(f"\n📊 Total interacciones: {len(dataset)}")
    for fuente, s in stats.items():
        print(f"   - {fuente}: {s['usadas']}/{s['total_crudo']} usadas")
    print(f"\nMás info: cat {PROCESSED_DIR / 'resumen_datos.json'}")


if __name__ == "__main__":
    main()