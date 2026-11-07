# 💙 Community Pulse

> **Hackathon ONE G10 — Oracle Next Education & Alura**

Convierte la actividad orgánica de una comunidad digital en **activos de marketing listos para publicar**: posts de LinkedIn, resúmenes para newsletters, FAQs, testimonios — y un **motor de decisiones** que detecta miembros en riesgo y deriva dudas recurrentes a mentorías.

---

## 🧭 Estructura del repositorio

| Ubicación | Contenido |
|-----------|-----------|
| [`communitylab/`](communitylab/) | Código del sistema: pipeline, análisis LLM, motor de decisiones, generadores, API y dashboard. Guía de instalación en [`communitylab/README.md`](communitylab/README.md). |
| [`arquitectura.md`](arquitectura.md) | Arquitectura técnica y diagramas. |
| [`plan_trabajo_semanal.md`](plan_trabajo_semanal.md) | Plan de trabajo del hackathon. |
| [`guia_modulos.md`](guia_modulos.md) | Guía de implementación por módulos. |
| [`modulo_toma_decisiones.md`](modulo_toma_decisiones.md) | Spec del motor de decisiones (diferencial). |
| [`analisis_datasets_reales.md`](analisis_datasets_reales.md) | Análisis de datasets reales y licencias. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Guía de contribución y convenciones. |

## 🚀 Arranque rápido

La guía completa está en [`communitylab/README.md`](communitylab/README.md). Resumen:

```bash
cd communitylab
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "COMMUNITYLAB_LLM_BACKEND=rule_based" >> .env

# Dashboard (demo sin credenciales)
COMMUNITYLAB_LLM_BACKEND=rule_based streamlit run src/interface/app.py

# Tests
python3 -m pytest tests/ -q
```

## ✨ Diferenciales

- **Motor de decisiones** híbrido (reglas + LLM): alertas de sentimiento, detección de miembros en riesgo y derivación a mentorías.
- **Backend offline `rule_based`** para demos, tests y CI sin necesidad de API keys.
- Arquitectura modular end-to-end: ingesta → análisis → decisiones → generadores → OCI Object Storage.

---

*Proyecto del Hackathon ONE G10 — Oracle Next Education & Alura.*
