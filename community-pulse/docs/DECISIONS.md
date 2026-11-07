# 📝 Registro de Decisiones Técnicas (ADR)

> Cada decisión debe agregarse aquí con fecha, responsable y justificación.
> Se actualiza durante todo el hackathon.

## ADR-001: Orquestación con Python puro (+ async)

- **Fecha:** Día 1
- **Responsable:** Tech Lead
- **Decisión:** Python con asyncio en vez de n8n
- **Por qué:** Mayor control, testing fácil, integración directa con módulos, sin dependencias externas de hosting
- **Alternativa considerada:** n8n (visual pero difícil de testear)

## ADR-002: LLM principal — Google Gemini

- **Fecha:** Día 1
- **Responsable:** Data Scientists
- **Decisión:** Gemini como proveedor principal, OpenAI como respaldo
- **Por qué:** Capa gratuita generosa, buena calidad en español/portugués
- **Alternativa considerada:** OpenAI (más caro), Claude (menor disponibilidad gratuita)

## ADR-003: Interfaz con Streamlit

- **Fecha:** Día 1
- **Responsable:** Software Engineer
- **Decisión:** Streamlit
- **Por qué:** Rápido de implementar, soporta estado (curaduría), integra bien con pandas
- **Alternativa considerada:** Gradio (mejor para demos de ML, peor para paneles de gestión)

## ADR-004: Persistencia en OCI Object Storage

- **Fecha:** Día 1
- **Responsable:** Backend Developer
- **Decisión:** OCI Object Storage como única persistencia
- **Por qué:** Requisito obligatorio del MVP + totalmente gratis en Always Free
- **Alternativa considerada:** Base de datos local (no aporta al checklist)

## ADR-005: Motor de decisiones híbrido (reglas + LLM)

- **Fecha:** Día 6
- **Responsable:** Tech Lead + DS
- **Decisión:** Reglas deterministas para casos críticos + LLM para matices
- **Por qué:** Las reglas garantizan comportamiento predecible; el LLM captura contexto
- **Alternativa considerada:** Solo LLM (impredecible en casos críticos), solo reglas (poco flexible)
