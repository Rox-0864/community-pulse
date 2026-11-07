# 📅 PLAN DE TRABAJO SEMANAL — Community Pulse

> **Duración total: 10 días hábiles**
> **Reunión diaria obligatoria: Daily Standup (15 min, primera hora del día)**
> **Responsable del seguimiento: Tech Lead + Backend Developer**

---

## 🗓️ DÍA 1 — Lunes: Cimientos

### 🎯 Objetivo del día
Que TODO el equipo sepa exactamente qué va a hacer, cómo se conecta su trabajo con el de los demás, y que la infraestructura base funcione.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Definir stack tecnológico final (LLM, framework de orquestación) | Documento DECISIONS.md con justificación | Ninguna |
| **Tech Lead** | Asignar ramas de Git a cada miembro | Tabla en CONTRIBUTING.md actualizada | Ninguna |
| **Data Architect** | Diseñar diagrama de arquitectura del pipeline completo | Diagrama Mermaid o Draw.io (guardar en docs/) | Ninguna |
| **Data Architect** | Definir esquema JSON de entrada y salida | Archivo docs/api-schema.json | Ninguna |
| **Backend Developer** | Crear repositorio en GitHub | Repo vacío con README, .gitignore, CONTRIBUTING.md | Ninguna |
| **Backend Developer** | Configurar branch protection en main | Configuración en GitHub Settings | Repo creado |
| **Backend Developer** | Crear estructura de carpetas del proyecto | Estructura de directorios en el repo | Repo creado |
| **Software Engineer** | Evaluar n8n vs Python puro para orquestación | Documento DECISIONS.md (sección orquestación) | Ninguna |
| **Software Engineer** | Configurar entorno de desarrollo (Python, dependencias) | requirements.txt funcional + venv | Repo creado |
| **Data Scientists (3)** | Evaluar LLMs: Gemini vs OpenAI vs Claude (costo, calidad, velocidad) | Documento DECISIONS.md (sección LLMs) | Ninguna |
| **Data Scientists (3)** | Instalar SDKs de LLMs elegidos, probar conexión básica | Notebook de prueba con "Hello World" del LLM | LLM elegido |
| **Data Analysts (2)** | Crear dataset simulado #1: mensajes de Discord realistas | Archivo data/simulados/discord_messages.json | Esquema definido |
| **Data Analysts (2)** | Definir categorías de sentimiento y tipos de contenido | Documento docs/content-categories.md | Ninguna |

### ✅ Checkpoint Día 1
- [ ] Repo creado y accesible para todos
- [ ] Cada miembro tiene su branch asignada
- [ ] Stack tecnológico definido y documentado
- [ ] Dataset simulado #1 listo
- [ ] Al menos 1 LLM funcionando (conexión verificada)

---

## 🗓️ DÍA 2 — Martes: Módulos Base

### 🎯 Objetivo del día
Que cada módulo funcione de forma aislada (unit). Nadie depende de nadie todavía.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Revisar que cada uno esté trabajando en su branch | Daily + verificación en GitHub | Día 1 |
| **Data Architect** | Crear diagrama de flujo de datos (input → process → output) | Diagrama en docs/ | Diagrama de arquitectura |
| **Data Architect** | Definir contratos de接口 entre módulos | Documento docs/module-contracts.md | Esquema JSON |
| **Backend Developer** | Crear módulo base de OCI: conexión + bucket creation | src/oci/oci_client.py funcional | Repo creado |
| **Backend Developer** | Crear función de upload a OCI (simulada con mock) | src/oci/storage.py con test básico | OCI client |
| **Software Engineer** | Crear módulo de orquestación base | src/orchestration/pipeline.py (estructura vacía) | Repo creado |
| **Software Engineer** | Crear interfaz Streamlit básica (solo splash screen) | src/interface/app.py funcional | Repo creado |
| **Data Scientist 1** | Crear módulo de análisis de sentimiento | src/analysis/sentiment.py funcional | LLM SDK instalado |
| **Data Scientist 2** | Crear módulo de categorización de temas | src/analysis/categorization.py funcional | LLM SDK instalado |
| **Data Scientist 3** | Crear sistema de puntuación de relevancia | src/analysis/relevance.py funcional | LLM SDK instalado |
| **Data Analyst A** | Crear dataset simulado #2: mensajes de Slack | Archivo data/simulados/slack_messages.json | Esquema |
| **Data Analyst B** | Crear dataset simulado #3: feedback de cursos | Archivo data/simulados/course_feedback.json | Esquema |

### ✅ Checkpoint Día 2
- [ ] Cada módulo funciona de forma aislada (test básico pasa)
- [ ] Módulo OCI conecta (con mock) y puede subir archivos
- [ ] Análisis de sentimiento retorna resultado para un mensaje de prueba
- [ ] 3 datasets simulados listos
- [ ] Contratos de接口 documentados

---

## 🗓️ DÍA 3 — Miércoles: Integración del Corazón

### 🎯 Objetivo del día
Conectar los módulos de análisis entre sí. El "cerebro" del sistema debe funcionar end-to-end.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Definir cómo se prueban los módulos integrados | Script de prueba o test de integración | Contratos definidos |
| **Data Architect** | Revisar que la integración respete los contratos | Documento de revisión | Módulos base |
| **Backend Developer** | Crear función de persistencia: resultado del análisis → JSON → OCI | src/oci/persistence.py | OCI mock + esquema |
| **Backend Developer** | Testear upload de resultado completo a OCI | Test end-to-end de persistencia | Persistence.py |
| **Software Engineer** | Integrar los 3 módulos de análisis en el pipeline | src/orchestration/analysis_pipeline.py | Los 3 módulos DS |
| **Software Engineer** | Crear bifurcación condicional: sentimiento → tipo de activo | src/orchestration/router.py | Pipeline de análisis |
| **Data Scientist 1** | Crear prompts de análisis de sentimiento (versión refinada) | src/prompts/sentiment_prompts.py | Sentiment.py funcional |
| **Data Scientist 2** | Crear prompts de categorización (few-shot learning) | src/prompts/categorization_prompts.py | Categorization.py funcional |
| **Data Scientist 3** | Crear prompts de puntuación de relevancia | src/prompts/relevance_prompts.py | Relevance.py funcional |
| **Data Analyst A** | Testear los 3 módulos DS con los 3 datasets | Documento de resultados en docs/test-results.md | Datasets + módulos DS |
| **Data Analyst B** | Crear métricas de calidad: precision/recall por categoría | Notebook en notebooks/quality-metrics.ipynb | Resultados de test |

### ✅ Checkpoint Día 3
- [ ] Pipeline de análisis procesa un mensaje y retorna: sentimiento + categoría + relevancia
- [ ] Bifurcación condicional funciona (sentimiento positivo → genera "caso de éxito")
- [ ] Resultados se pueden persistir en OCI (con mock)
- [ ] Prompts refinados y documentados
- [ ] Primer reporte de calidad de análisis

---

## 🗓️ DÍA 4 — Jueves: Generadores de Contenido

### 🎯 Objetivo del día
Que el sistema pueda generar al menos 2 formatos de activos de marketing a partir de datos procesados.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Verificar que el pipeline completo funcione (ingesta → análisis → routing) | Test de integración completo | Día 3 |
| **Data Architect** | Documentar flujo de datos actual vs diseño original | Documento de gap analysis | Pipeline funcionando |
| **Backend Developer** | Crear función de empaquetado de activos (JSON structure) | src/oci/package_assets.py | Pipeline + OCI |
| **Backend Developer** | Testear empaquetado completo: análisis + activos → OCI | Test end-to-end | Package_assets.py |
| **Software Engineer** | Crear generador #1: Post para LinkedIn | src/generators/linkedin_generator.py | Routing funcional |
| **Software Engineer** | Crear generador #2: Resumen de Newsletter semanal | src/generators/newsletter_generator.py | Routing funcional |
| **Data Scientist 1** | Crear prompts para LinkedIn (tono inspirador, hashtags, CTA) | src/prompts/linkedin_prompts.py | Generadores base |
| **Data Scientist 2** | Crear prompts para Newsletter (resumen ejecutivo, highlights) | src/prompts/newsletter_prompts.py | Generadores base |
| **Data Scientist 3** | Crear generador #3: Caso de éxito / testimonio | src/generators/testimonial_generator.py | Routing funcional |
| **Data Analyst A** | Evaluar calidad de los posts generados (scoring 1-10) | Tabla de scoring en docs/quality-scores.md | Generadores |
| **Data Analyst B** | Crear generador #4: FAQ / Tip rápido | src/generators/faq_generator.py | Routing funcional |

### ✅ Checkpoint Día 4
- [ ] Generador LinkedIn produce posts con tono correcto y hashtags
- [ ] Generador Newsletter produce resúmenes ejecutivos
- [ ] Al menos 2 generadores más funcionando
- [ ] Activos empaquetados y subidos a OCI (mock)
- [ ] Primera evaluación de calidad de contenido

---

## 🗓️ DÍA 5 — Viernes: Orquestación Completa + OCI Real

### 🎯 Objetivo del día
El pipeline funcione de punta a punta con OCI real. Primera demo interna.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Coordinar integración completa del pipeline | Pipeline end-to-end funcionando | Todos los módulos |
| **Data Architect** | Revisar que la arquitectura implementada respete el diseño | Documento de validación | Pipeline completo |
| **Backend Developer** | Configurar OCI REAL (bucket Always Free) | Bucket creado en OCI Console + credenciales | Cuenta OCI |
| **Backend Developer** | Reemplazar mock de OCI por conexión real | src/oci/oci_client.py (versión real) | Bucket real |
| **Backend Developer** | Testear upload real a OCI | Test con archivo real subido a OCI | OCI real |
| **Software Engineer** | Integrar orquestación completa: ingest → analysis → routing → generation → storage | src/orchestration/full_pipeline.py | Generadores + OCI real |
| **Software Engineer** | Crear webhook o trigger de entrada (recibe JSON) | src/ingest/webhook.py o src/ingest/file_loader.py | Pipeline completo |
| **Data Scientist 1** | Optimizar prompts de sentimiento basándose en calidad del día 4 | Prompts refinados v2 | Quality scores |
| **Data Scientist 2** | Optimizar prompts de generación (LinkedIn + Newsletter) | Prompts refinados v2 | Quality scores |
| **Data Scientist 3** | Testear pipeline con los 3 datasets completos | Resultados en docs/full-test-results.md | Pipeline completo |
| **Data Analyst A** | Preparar presentación ejecutiva: qué hace el producto | Diapositivas o documento en docs/demo-script.md | Pipeline funcionando |
| **Data Analyst B** | Crear dashboard básico de métricas en Streamlit | src/interface/metrics_dashboard.py | Pipeline + datos |

### ✅ Checkpoint Día 5 — ⭐ MILESTONE: PRIMERA DEMO
- [ ] Pipeline completo funciona: recibe JSON → genera activos → guarda en OCI
- [ ] OCI real funciona (archivos visibles en bucket)
- [ ] Al menos 2 generadores producen contenido de calidad
- [ ] Demo interna exitosa con los 3 datasets
- [ ] Primera versión de la presentación ejecutiva

---

## 🗓️ DÍA 6 — Lunes: Interfaz y Curaduría

### 🎯 Objetivo del día
La interfaz funcione para que el equipo de marketing pueda ver, aprobar y editar publicaciones.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Definir UX del panel de curaduría | Wireframe o mockup simple | Demo del día 5 |
| **Data Architect** | Documentar decisiones técnicas tomadas hasta ahora | docs/decisions-log.md | Todo el trabajo |
| **Backend Developer** | Crear API REST simple para la interfaz | src/api/endpoints.py | Pipeline completo |
| **Backend Developer** | Conectar API con el pipeline de orquestación | Integración API + pipeline | API creada |
| **Software Engineer** | Crear panel de curaduría en Streamlit | src/interface/curaduria.py | API funcionando |
| **Software Engineer** | Funcionalidades: ver posts, editar, aprobar, rechazar | Streamlit con estado | Panel base |
| **Data Scientist 1** | Agregar generador de imágenes (banner/tarjeta) | src/generators/image_generator.py (opcional) | Generadores |
| **Data Scientist 2** | Crear sistema de calidad automática (score de cada post) | src/analysis/quality_scorer.py | Generadores |
| **Data Scientist 3** | Testear interfaz con diferentes escenarios | Documento de testing en docs/ | Interfaz |
| **Data Analyst A** | Agregar visualizaciones al dashboard: sentimiento, temas, tendencias | Gráficos en Streamlit | Dashboard base |
| **Data Analyst B** | Crear vista de "Community Highlights" (resumen semanal visual) | src/interface/highlights.py | Pipeline |

### ✅ Checkpoint Día 6
- [ ] Panel de curaduría funcional: ver, editar, aprobar posts
- [ ] Dashboard con métricas de sentimiento y temas
- [ ] Vista de Community Highlights operativa
- [ ] API REST responde correctamente
- [ ] La interfaz se ve profesional

---

## 🗓️ DÍA 7 — Martes: End-to-End + Diferenciales

### 🎯 Objetivo del día
Todo funcione sin intervención manual. Empezar con los opcionales que dan puntos extra.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Test end-to-end completo con los 3 datasets | Checklist de aprobación completo | Todo funcional |
| **Tech Lead** | Identificar qué diferenciales son viables para implementar | Lista priorizada en docs/differentials.md | Test E2E |
| **Backend Developer** | Implementar cola de procesamiento asíncrono (si hay tiempo) | src/orchestration/async_queue.py (opcional) | Pipeline |
| **Backend Developer** | Crear endpoint de health check y monitoreo | src/api/health.py | API |
| **Software Engineer** | Implementar diferencial: Bot de Discord/Telegram | src/bot/community_bot.py (opcional) | Pipeline |
| **Software Engineer** | Agregar autenticación básica a la interfaz | src/interface/auth.py (opcional) | Interfaz |
| **Data Scientist 1** | Crear notebook completo de demo (ejecutable de punta a punta) | notebooks/demo_complete.ipynb | Todo |
| **Data Scientist 2** | Optimizar prompts para los 3 escenarios reales | Prompts v3 finales | Calidad |
| **Data Scientist 3** | Implementar few-shot learning con ejemplos reales del dataset | Prompts mejorados | Datasets |
| **Data Analyst A** | Crear 3 casos de demo pre-armados (happy path, edge case, error) | docs/demo-cases/ | Pipeline |
| **Data Analyst B** | Preparar métricas de impacto: cuánto tiempo ahorra vs manual | Documento en docs/impact-metrics.md | Datos |

### ✅ Checkpoint Día 7
- [ ] Pipeline E2E funciona sin intervención manual
- [ ] 3 casos de demo listos y probados
- [ ] Al menos 1 diferencial implementado
- [ ] Notebook de demo ejecutable
- [ ] Métricas de impacto documentadas

---

## 🗓️ DÍA 8 — Miércoles: Testing y Pulido

### 🎯 Objetivo del día
Encontrar y corregir bugs. Todo debe funcionar robustamente.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Coordinar session de bug fixing | Lista de bugs priorizada | Testing |
| **Data Architect** | Validar que el esquema de salida cumpla el formato del PDF | Checklist de conformidad | Pipeline |
| **Backend Developer** | Manejo de errores: qué pasa si OCI se cae, si el LLM falla, si el input es inválido | Error handling en todos los módulos | E2E |
| **Backend Developer** | Logging: registrar cada paso del pipeline | src/utils/logger.py | Todo |
| **Software Engineer** | UX polish: loading states, mensajes de error amigables | Interface refinada | E2E |
| **Software Engineer** | Test de estrés: 100 mensajes simultáneos | Resultado del stress test | Pipeline |
| **Data Scientist 1** | Bug fixes en análisis de sentimiento | Código corregido | Bugs identificados |
| **Data Scientist 2** | Bug fixes en generadores de contenido | Código corregido | Bugs identificados |
| **Data Scientist 3** | Validar outputs con los 3 datasets | docs/validation-report.md | Bugs |
| **Data Analyst A** | Test de aceptación: 10 mensajes random → validar calidad | docs/acceptance-test.md | Pipeline |
| **Data Analyst B** | Limpiar y organizar documentación | README.md actualizado | Todo |

### ✅ Checkpoint Día 8
- [ ] 0 bugs críticos abiertos
- [ ] Manejo de errores funcional en todos los caminos
- [ ] Logging activo y funcional
- [ ] Interface pulida y con feedback visual
- [ ] Validación de outputs contra el formato del PDF

---

## 🗓️ DÍA 9 — Jueves: Documentación y Preparación

### 🎯 Objetivo del día
Todo documentado, README completo, demo practicada.

---

| Rol | Tarea | Entregable | Dependencia |
|-----|-------|------------|-------------|
| **Tech Lead** | Ensayar la demo completa cronometrada | Demo practiced in <10 min | Todo documentado |
| **Data Architect** | Completar diagrama de arquitectura final | docs/architecture-final.md con Mermaid | Validación |
| **Backend Developer** | Completar README.md con guía de despliegue paso a paso | README.md final | Todo |
| **Backend Developer** | Documentar configuración de OCI (sin credenciales) | docs/oci-setup-guide.md | OCI funcionando |
| **Software Engineer** | Crear video corto de demo (si aplica) o GIFs de la interfaz | assets/demo-video/ | Interfaz |
| **Software Engineer** | Verificar que la app corra desde cero (fresh install) | Test de install clean | README |
| **Data Scientist 1** | Documentar notebook de demo con explicaciones | notebooks/demo_complete.ipynb (con markdown) | Notebook |
| **Data Scientist 2** | Documentar system prompts y su evolución | docs/prompts-guide.md | Prompts |
| **Data Scientist 3** | Crear sección "Resultados" del README | README sección de resultados | Test results |
| **Data Analyst A** | Crear presentación ejecutiva final | docs/presentation/ | Todo |
| **Data Analyst B** | Preparar datos para la demo (3 escenarios listos) | data/demo/ | Datasets |

### ✅ Checkpoint Día 9
- [ ] README.md completo y profesional
- [ ] Demo ensayada y dentro del tiempo
- [ ] Documentación de arquitectura final
- [ ] Presentación ejecutiva lista
- [ ] Fresh install funciona

---

## 🗓️ DÍA 10 — Viernes: Demo Final 🚀

### 🎯 Objetivo del día
Presentar el proyecto. ¡A ganar!

---

| Rol | Tarea | Entregable |
|-----|-------|------------|
| **Tech Lead** | Coordinar el orden de la presentación | Run of show |
| **Tech Lead** | Presentar: visión general del problema y solución | Primeros 2 min |
| **Data Architect** | Presentar: diagrama de arquitectura y decisiones técnicas | 2-3 min |
| **Backend Developer** | Presentar: integración con OCI y demo en vivo | 3-5 min |
| **Software Engineer** | Presentar: interfaz y funcionalidades | 3-5 min |
| **Data Scientists** | Presentar: análisis de sentimiento y calidad de contenido | 2-3 min |
| **Data Analysts** | Presentar: métricas de impacto y antes/después | 2-3 min |

### ✅ Checkpoint Día 10
- [ ] Demo presentada
- [ ] Preguntas del jurado respondidas
- [ ] Repositorio público y accesible
- [ ] ¡PROYECTO COMPLETADO! 🎉

---

## 📊 Mapa de Dependencias Críticas

```
Día 1          Día 2          Día 3          Día 4          Día 5
  │              │              │              │              │
  ├─ Stack ─────►├─ Módulos ───►├─ Integración►├─ Generadores►├─ E2E + OCI Real
  ├─ Repo ──────►├─ Branches ──►│              │              │
  ├─ Esquema ───►├─ Datasets ──►├─ Tests ─────►│              │
  └─ LLM SDK ───►└─ Prompts ───►└─ Prompts v2 ►└─ Prompts v3 ►└─ Demo Interna
                                                                   │
Día 6          Día 7          Día 8          Día 9          Día 10
  │              │              │              │              │
  ├─ Interfaz ──►├─ Diferenciales►├─ Bug Fix ──►├─ Docs ──────►├─ DEMO FINAL
  ├─ Dashboard ─►├─ E2E Test ──►├─ Pulido ────►├─ Ensayo ────►│
  └─ Curaduría ─►└─ 3 Casos ───►└─ Validación ►└─ Presentación►│
```

---

## 🚨 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| OCI Always Free tiene límites | Alta | Alto | Testear con pocos archivos, tener plan B (local) |
| LLM gratuito tiene rate limits | Alta | Medio | Usar 2 LLMs como fallback, cachear respuestas |
| Alguien se enferma/ausenta | Media | Alto | Documentación clara, que 2 personas conozcan cada módulo |
| Git conflicts graves | Media | Medio | Daily rebase, BE resuelve rápido |
| Calidad del contenido generada pobre | Media | Alto | Iterar prompts, few-shot learning, QA constante |
| La interfaz tarda en cargar | Baja | Medio | Async processing, loading states |

---

## 📋 Checklist Final de Evaluación (del PDF)

| Requisito | Responsable | Día de entrega | Estado |
|-----------|-------------|----------------|--------|
| ☐ Ingesta funcional de interacciones | SE + DA | Día 5 | ⬜ |
| ☐ Análisis de sentimiento con LLMs | DS1 + DS2 | Día 3 | ⬜ |
| ☐ Generación de 2+ formatos de activos | SE + DS3 | Día 4 | ⬜ |
| ☐ Orquestación del flujo (n8n/Python) | SE | Día 5 | ⬜ |
| ☐ Integración con OCI Object Storage | BE | Día 5 | ⬜ |
| ☐ Demo de 3 ejemplos de transformación | Todos | Día 9 | ⬜ |
| ☐ Repositorio GitHub con documentación | BE + DA | Día 9 | ⬜ |

---

*Plan creado el Día 0 — listo para ejecutar*
*Revisar y ajustar en la daily del Día 1*
