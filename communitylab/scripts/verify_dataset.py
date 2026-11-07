"""
CommunityLab — Verifica que los datos cumplan el contrato del pipeline.

Uso:
    python scripts/verify_dataset.py                          # Valida el dataset combinado
    python scripts/verify_dataset.py --file data/real/x.json  # Valida un archivo específico
    python scripts/verify_dataset.py --quiet                  # Solo código de salida (0=ok)

El contrato mínimo por interacción:
    {
        "autor":  str,
        "canal":  str (empieza con # o r/),
        "tipo":   str en {general, pregunta_tecnica, logro, feedback, testimonio},
        "texto":  str no vacío,
        "timestamp": str,
    }
"""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TIPOS_VALIDOS = {"general", "pregunta_tecnica", "logro", "feedback", "testimonio"}
ERRORES = []


def check_interaccion(i, idx, origen):
    """Valida una interacción y acumula errores."""
    error_base = f"[{origen} #{idx}]"

    if not isinstance(i, dict):
        ERRORES.append(f"{error_base} No es un objeto: {type(i).__name__}")
        return

    for campo in ("id", "autor", "canal", "tipo", "texto", "timestamp", "origen"):
        if campo not in i:
            ERRORES.append(f"{error_base} Falta campo '{campo}'")

    texto = i.get("texto", "")
    if not isinstance(texto, str) or len(texto.strip()) < 10:
        ERRORES.append(f"{error_base} 'texto' vacío o < 10 caracteres (rechazado por MessageSchema)")

    tipo = i.get("tipo", "")
    if tipo not in TIPOS_VALIDOS:
        ERRORES.append(f"{error_base} 'tipo' inválido: {tipo!r} (válidos: {sorted(TIPOS_VALIDOS)})")

    canal = i.get("canal", "")
    if not (canal.startswith("#") or canal.startswith("r/")):
        ERRORES.append(f"{error_base} 'canal' sin formato (# o r/): {canal!r}")

    autor = i.get("autor", "")
    if not isinstance(autor, str) or not autor.strip():
        ERRORES.append(f"{error_base} 'autor' vacío")


def main():
    parser = argparse.ArgumentParser(description="Verifica formato del dataset CommunityLab")
    parser.add_argument("--file", type=str, default=None, help="Archivo a validar (default: dataset_combinado)")
    parser.add_argument("--quiet", action="store_true", help="Solo código de salida")
    args = parser.parse_args()

    if args.file:
        ruta = Path(args.file)
    else:
        ruta = BASE_DIR / "data" / "processed" / "dataset_combinado.json"

    if not ruta.exists():
        print(f"❌ No existe: {ruta}. Ejecuta download_datasets.py + prepare_samples.py primero.")
        sys.exit(2)

    with open(ruta, "r", encoding="utf-8") as f:
        paquete = json.load(f)

    interacciones = paquete.get("interacciones", [])
    origen = paquete.get("origen_comunidad", ruta.stem)

    for i, interaccion in enumerate(interacciones):
        check_interaccion(interaccion, i, origen)

    if not args.quiet:
        print(f"📋 Archivo: {ruta}")
        print(f"📦 Origen: {origen}")
        print(f"🔢 Interacciones: {len(interacciones)}")
        print(f"❌ Errores: {len(ERRORES)}")

        if ERRORES:
            for e in ERRORES[:20]:
                print(f"   - {e}")
            if len(ERRORES) > 20:
                print(f"   ... y {len(ERRORES) - 20} más")
        else:
            print("✅ El dataset cumple el contrato del pipeline")

    sys.exit(0 if not ERRORES else 1)


if __name__ == "__main__":
    main()