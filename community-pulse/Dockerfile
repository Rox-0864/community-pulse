# ============================================
# Community Pulse — Imagen Docker
# ============================================
# Imagen única y multi-propósito: según el `command` sirve la API
# (uvicorn) o el dashboard (Streamlit). El bot de Discord puede
# levantarse desde la misma imagen.
#
# Responsable: Backend Developer
# ============================================

FROM python:3.11-slim

# Buenas prácticas: no escribir bytecode, salida sin buffer, sin cache pip.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# curl solo para el healthcheck del contenedor.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Capa cacheable: primero las dependencias, después el código.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Código fuente + dataset de demo (solo lo que está versionado).
COPY src ./src
COPY data/sample ./data/sample

# Usuario sin privilegios (la app solo lee; no necesita root).
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000 8501

# Por defecto levanta la API; compose sobreescribe esto para Streamlit.
CMD ["uvicorn", "src.api.endpoints:app", "--host", "0.0.0.0", "--port", "8000"]
