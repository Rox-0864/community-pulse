# Preguntas de Seguimiento — Cuestionario Tech Lead CommunityLab

## Instrucciones de uso

Para cada respuesta del candidato, usa las preguntas de la columna "Si responde X" para profundizar.
No son obligatorias todas — solo las que revelan puntos débiles o ambiguos.

---

## BLOQUE 1: Visión Sistémica

### P1. Flujo completo (mensaje Discord → post LinkedIn → nube)

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| Solo habla de su área | "¿Y cómo se conecta eso con los datos de entrada? ¿Quién transforma el mensaje en algo procesable?" |
| Solo menciona secuencias | "¿Dónde pondrías un punto de fallo? ¿Qué pasa si el LLM devuelve un error a mitad del proceso?" |
| Secuencia correcta pero sin tecnologías | "¿Con qué herramienta concreta implementarías la orquestación? ¿Qué ventaja te da en este caso?" |
| Completo pero sin datos | "¿Dónde se almacenan los datos intermedios entre cada etapa? ¿En memoria, en archivo, en base de datos?" |

### P2. LLM tarda 30 segundos

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| "Buscamos otro LLM" | "¿Qué pasa si el problema es que el prompt tiene demasiado contexto? ¿Cómo lo diagnosticás antes de cambiar de modelo?" |
| "Async / cola de espera" | "El usuario hace clic y se va. ¿Cómo le avisás cuando el post esté listo? ¿Podés usar webhook o polling? ¿Cuál y por qué?" |
| Respuesta completa | "Si tuvieras que hacerlo con un presupuesto de $0 (capa Always Free), ¿qué cambiaría de tu solución?" |

---

## BLOQUE 2: Capacidad de Ejecución

### P3. Dependencia bloqueada (OCI llega día 7)

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| "Espero a que esté OCI" | "¿Qué podés construir hoy con una SDK mock de OCI que te sirva después? ¿Cómo validás que la interfaz funcione sin el servicio real?" |
| "Avanzo con otras tareas" | "Específicamente, ¿qué tarea? ¿Quién la hace, con qué deadline?" |
| Solución con mock | "¿Cómo te asegurás de que el mock se parezca al servicio real? ¿Qué testeás con el mock y qué NO podés testear?" |

### P4. Código desordenado pero funcional

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| "Lo reescribo yo" | "¿Y si hay 2 personas con código desordenado? ¿Reescribís todo? ¿Cuál es el rol del code review en tu equipo?" |
| "Le digo que lo arregle" | "¿Y si no sabe cómo? ¿Le das solo la crítica o también la guía? ¿Cómo hacés que la corrección sea aprendizaje?" |
| Code review pedagógico | "¿Cómo balanceás el código "perfecto" contra el deadline del hackathon? ¿Cuándo decís 'esto alcanza para hoy'?" |

---

## BLOQUE 3: Dominio Técnico

### P5. Pipeline de orquestación

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| Confunde concepto | "¿Diferencia entre una función que llama otra (secuencia) y una orquestación real con reintentos y estados?" |
| Concepto pero sin implementación | "Si lo implementás en Python, ¿usás alguna librería? ¿Cuándo usarías n8n en vez de código?" |
| Respuesta completa | "¿Qué pasa si el nodo de sentimiento recibe un input vacío? ¿Quién maneja ese error: el pipeline, el LLM o la capa de entrada?" |

### P6. Webhook vs cron vs pub/sub

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| No distingue | "¿Qué problema resuelve cada uno? Dame un caso real de uso para cada uno en este proyecto." |
| Distingue pero no elige | "Si Discord evita webhooks (rate limit), ¿Qué alternativa usás para ingesta sin perder datos?" |
| Elige correctamente | "¿Qué pasa si el webhook se cae y Discord reenvía el mensaje? ¿Cómo evitás procesar el mismo mensaje 2 veces?" |

---

## BLOQUE 4: Liderazgo y Comunicación

### P7. Daily standup con 3 problemas simultáneos

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| Responde a cada uno | "¿Qué está bloqueando el avance del equipo HOY? ¿Uno de esos tres temas es más crítico que los otros?" |
| Prioriza correctamente | "¿Cómo hacés seguimiento de los 3 temas después de la reunión? ¿Qué herramienta o ritual usás para no perder el hilo?" |
| Detecta el problema de fondo | "Si el equipo no tiene claros los roles, ¿cómo lo resolvés sin parecer que estás tomando el control?" |

### P8. Explicar a un non-tech en 30 seg

| Si responde... | Pregunta de seguimiento |
|----------------|------------------------|
| Usa jerga técnica | "Reintentá: ¿cómo se lo contarías a tu abuela o a un directivo de marketing?" |
| Se va por las ramas | "Ahora decímelo en UNA oración." — luego: "¿Qué 3 datos concretos creés que le importan más a ese cliente?" |
| Claro y conciso | "¿Qué métrica usarías en la demo para que el cliente vea el valor en 5 segundos? ¿Un número, una visualización, un testimonio?" |

---

## NOTAS DE EVALUACIÓN

- **Tiempo máximo por candidato:** 15 min
- **Registrá la PRIMERA respuesta** antes del follow-up — es la más reveladora
- **Evaluá también la velocidad de reacción:** ¿responde rápido o necesita pensar 2 minutos? En un hackathon, velocidad importa
- **Pregunta extra (solo si hay empate técnico):** "Contame de un momento donde algo se rompió a mitad de un proyecto y cómo lo manejaste" — no importa el ámbito (trabajo, estudio, personal)