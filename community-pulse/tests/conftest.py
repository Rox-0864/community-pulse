"""Configuración compartida de tests."""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
