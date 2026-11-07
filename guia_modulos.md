# 🧭 GUÍA TÉCNICA POR MÓDULO — Community Pulse

> **Para cada módulo encontrarás:**
> - 🎯 Qué hace (responsabilidad única)
> - 📥 Entrada / 📤 Salida
> - 🛠️ Tecnologías
> - 📁 Estructura de archivos
> - 🔑 Funciones clave con ejemplos
> - 🧪 Cómo testearlo
> - ⚠️ Errores comunes

---

# 1️⃣ MÓDULO: INGEST

> **Responsable:** Software Engineer + Data Analysts
> **Rama:** `feat/ingesta`

## 🎯 Qué hace
Recibe datos de comunidades digitales (Discord, Slack, foros, CSV, JSON) y los normaliza a un formato estándar que el resto del sistema puede procesar.

## 📥 Entrada
```json
// Cualquiera de estas fuentes:
- JSON directo (API, webhook)
- CSV exportado de Discord/Slack
- Archivo plano con mensajes
```

## 📤 Salida
```json
{
  "id": "msg_001",
  "autor": "Mariana Souza",
  "canal": "#logros-y-empleos",
  "tipo": "testimonio",
  "texto": "Quede seleccionada para el puesto de...",
  "timestamp": "2026-09-10T14:30:00Z",
  "origen": "discord",
  "metadata": {
    "reacciones": 12,
    "respuestas": 5
  }
}
```

## 🛠️ Tecnologías
- Python 3.10+
- `json`, `csv` (stdlib)
- `pydantic` para validación de schemas (opcional pero recomendado)

## 📁 Estructura
```
src/ingest/
├── __init__.py
├── loader.py          ← Carga archivos (JSON, CSV)
├── normalizer.py      ← Convierte a formato estándar
└── validators.py      ← Valida que los datos sean correctos
```

> **Nota (implementado el Día 2):** el webhook NO vive en `ingest/` — vive en la API
> junto con su worker asíncrono:
> ```
> src/api/
> ├── endpoints.py      ← POST /webhook (retorna 202 + job_id) + GET /jobs/{id}
> └── worker.py         ← JobWorker: cola asyncio + procesamiento en background
> ```
> El `ingest/` carga archivos (lote); `api/` recibe HTTP en tiempo real.
> Ambos terminan normalizando con el MISMO `normalizer.py`.

## 🔑 Funciones clave

### `loader.py`
```python
import json
import csv
from pathlib import Path

def load_json(filepath: str) -> list[dict]:
    """Carga un archivo JSON con mensajes de la comunidad."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Puede ser una lista directamente o tener una key 'interacciones'
    if isinstance(data, list):
        return data
    return data.get('interacciones', [])

def load_csv(filepath: str) -> list[dict]:
    """Carga un CSV y lo convierte a lista de diccionarios."""
    messages = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)
    return messages

def load_community_data(filepath: str) -> list[dict]:
    """Detecta el formato y carga automáticamente."""
    path = Path(filepath)
    if path.suffix == '.json':
        return load_json(filepath)
    elif path.suffix == '.csv':
        return load_csv(filepath)
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}")
```

### `normalizer.py`
```python
from datetime import datetime

# Mapa de canales a categorías
CHANNEL_MAP = {
    "#logros-y-empleos": "logro",
    "#dudas-langgraph": "pregunta_tecnica",
    "#feedback-cursos": "feedback",
    "#general": "general",
}

def normalize_message(raw: dict, origen: str = "discord") -> dict:
    """Normaliza un mensaje al formato estándar del sistema."""
    return {
        "id": f"msg_{hash(raw.get('texto', '')) % 10000:04d}",
        "autor": raw.get("autor", "Anónimo"),
        "canal": raw.get("canal", "general"),
        "tipo": CHANNEL_MAP.get(raw.get("canal", ""), raw.get("tipo", "general")),
        "texto": raw.get("texto", "").strip(),
        "timestamp": raw.get("timestamp", datetime.now().isoformat()),
        "origen": origen,
        "metadata": {
            "reacciones": raw.get("reacciones", 0),
            "respuestas": raw.get("respuestas", 0),
        }
    }

def normalize_batch(messages: list[dict], origen: str = "discord") -> list[dict]:
    """Normaliza un lote de mensajes."""
    return [normalize_message(msg, origen) for msg in messages if msg.get("texto")]
```

### `validators.py`
```python
from pydantic import BaseModel, Field
from typing import Optional

class MessageSchema(BaseModel):
    id: str
    autor: str
    canal: str
    tipo: str = Field(..., pattern="^(testimonio|pregunta_tecnica|feedback|logro|general)$")
    texto: str = Field(..., min_length=10, max_length=5000)
    timestamp: str
    origen: str

def validate_message(message: dict) -> bool:
    """Valida que un mensaje cumple el esquema."""
    try:
        MessageSchema(**message)
        return True
    except Exception as e:
        print(f"Error de validación: {e}")
        return False

def validate_batch(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Retorna (válidos, inválidos)."""
    validos = []
    invalidos = []
    for msg in messages:
        if validate_message(msg):
            validos.append(msg)
        else:
            invalidos.append(msg)
    return validos, invalidos
```

## 🧪 Cómo testearlo
```python
# tests/test_ingest.py
from src.ingest.loader import load_json
from src.ingest.normalizer import normalize_batch
from src.ingest.validators import validate_batch

def test_load_json():
    messages = load_json("data/simulados/discord_messages.json")
    assert len(messages) > 0
    assert "texto" in messages[0]

def test_normalize():
    raw = [{"autor": "Test", "canal": "#logros", "texto": "Hola mundo"}]
    normalized = normalize_batch(raw)
    assert normalized[0]["tipo"] == "logro"

def test_validate():
    valid = [{"id": "1", "autor": "A", "canal": "#x", "tipo": "general", "texto": "Test message", "timestamp": "2026-01-01", "origen": "discord"}]
    v, inv = validate_batch(valid)
    assert len(v) == 1
```

## ⚠️ Errores comunes
| Error | Causa | Solución |
|-------|-------|----------|
| `JSONDecodeError` | Archivo mal formateado | Validar encoding UTF-8, usar `json.load` con `try/except` |
| Mensajes vacíos | CSV con columnas vacías | Filtrar con `if msg.get("texto")` antes de procesar |
| Tipos incorrectos | Canal no está en CHANNEL_MAP | Usar `.get()` con valor por defecto, no `[]` |
| Duplicados | Mismo mensaje procesado 2 veces | Usar hash del texto como ID |

---

# 2️⃣ MÓDULO: ANALYSIS

> **Responsable:** Data Scientists (3 personas)
> **Rama:** `feat/sentiment` / `feat/analysis`

## 🎯 Qué hace
Analiza cada mensaje de la comunidad para extraer: sentimiento, temas principales, relevancia para marketing y entidades clave (personas, tecnologías, empresas).

## 📥 Entrada
```json
{
  "id": "msg_001",
  "autor": "Mariana Souza",
  "texto": "Quede seleccionada para el puesto de Desarrolladora Junior de IA!",
  "canal": "#logros-y-empleos"
}
```

## 📤 Salida
```json
{
  "id": "msg_001",
  "analisis": {
    "sentimiento": {
      "etiqueta": "muy_positivo",
      "score": 0.95,
      "confianza": 0.92
    },
    "temas": [
      {"tema": "contratacion", "relevancia": 0.98},
      {"tema": "portfolio", "relevancia": 0.85}
    ],
    "entidades": [
      {"nombre": "Mariana Souza", "tipo": "persona"},
      {"nombre": "LangChain", "tipo": "tecnologia"},
      {"nombre": "OCI", "tipo": "tecnologia"}
    ],
    "relevancia_marketing": {
      "score": 0.92,
      "razon": "Testimonio de éxito con contratación laboral"
    },
    "categoria_sugerida": "caso_exito"
  }
}
```

## 🛠️ Tecnologías
- LLM elegido (Gemini/OpenAI/Claude)
- `langchain` (opcional, para chains)
- Python 3.10+

## 📁 Estructura
```
src/analysis/
├── __init__.py
├── sentiment.py       ← Análisis de sentimiento
├── categorization.py  ← Clasificación de temas
├── relevance.py       ← Puntuación de relevancia
├── entities.py        ← Extracción de entidades
└── orchestrator.py    ← Orquesta los 3 análisis
```

## 🔑 Funciones clave

### `sentiment.py`
```python
from src.prompts.sentiment_prompts import SENTIMENT_SYSTEM_PROMPT

def analyze_sentiment(text: str, llm_client) -> dict:
    """
    Analiza el sentimiento de un texto usando un LLM.
    
    Args:
        text: El mensaje de la comunidad
        llm_client: Cliente del LLM (Gemini/OpenAI/Claude)
    
    Returns:
        dict con etiqueta, score y confianza
    """
    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",  # o el modelo elegido
        messages=[
            {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analiza el sentimiento de este mensaje:\n\n{text}"}
        ],
        response_format={"type": "json_object"}
    )
    
    # Parsear respuesta del LLM
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "etiqueta": result.get("sentiment", "neutral"),
        "score": result.get("score", 0.5),
        "confianza": result.get("confidence", 0.7)
    }
```

### `categorization.py`
```python
def categorize_message(text: str, canal: str, llm_client) -> list[dict]:
    """
    Categoriza un mensaje en temas predefinidos.
    
    Categorías posibles:
    - contratacion_logro
    - duda_tecnica
    - feedback_positivo
    - feedback_negativo
    - sugerencia
    - testimonio
    - general
    """
    prompt = f"""Categoriza este mensaje de la comunidad en UNA o MÁS categorías.
    
    Canal: {canal}
    Mensaje: {text}
    
    Categorías disponibles:
    - contratacion_logro:_logros laborales, entrevistas, contrataciones
    - duda_tecnica:preguntas sobre código, herramientas, conceptos
    - feedback_positivo:elogios, agradecimientos, experiencias buenas
    - feedback_negativo:quejas, problemas, dificultades
    - sugerencia:ideas de mejora, peticiones de features
    - testimonio:historias personales de superación
    - general:conversación casual, off-topic
    
    Retorna JSON con: categorias (lista), confianza (float)
    """
    
    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un分类器 de contenido de comunidades."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    return json.loads(response.choices[0].message.content)
```

### `relevance.py`
```python
def score_relevance(text: str, analisis_previo: dict, llm_client) -> dict:
    """
    Puntúa qué tan relevante es un mensaje para marketing.
    
    Criterios:
    - Menciona resultados concretos (empleo, proyecto, certificación)
    - Tiene carga emocional positiva
    - Es compartible (otros se identifican)
    - Menciona tecnologías del stack
    """
    prompt = f"""Evalúa qué tan relevante es este mensaje para crear contenido de marketing.
    
    Mensaje: {text}
    Sentimiento detectado: {analisis_previo.get('sentimiento', {}).get('etiqueta')}
    Categorías: {analisis_previo.get('categorias')}
    
    Califica del 0 al 1:
    - shareability: ¿Lo compartirías en redes?
    - emotion: ¿Genera emoción?
    - inspiration: ¿Inspira a otros?
    - brand_alignment: ¿Alineado con marca ONE/Alura?
    
    Retorna JSON con scores individuales y un promedio ponderado.
    """
    
    response = llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un editor de contenido de marketing tech."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "score": result.get("promedio_ponderado", 0.5),
        "desglose": result,
        "razon": result.get("justificacion", "")
    }
```

### `orchestrator.py`
```python
from src.analysis.sentiment import analyze_sentiment
from src.analysis.categorization import categorize_message
from src.analysis.relevance import score_relevance

def full_analysis(message: dict, llm_client) -> dict:
    """
    Ejecuta el análisis completo de un mensaje.
    
    Pipeline:
    1. Sentimiento → 2. Categorización → 3. Relevancia
    """
    text = message.get("texto", "")
    
    # Paso 1: Sentimiento
    sentimiento = analyze_sentiment(text, llm_client)
    
    # Paso 2: Categorización
    categorias = categorize_message(text, message.get("canal", ""), llm_client)
    
    # Paso 3: Relevancia
    relevancia = score_relevance(
        text, 
        {"sentimiento": sentimiento, "categorias": categorias},
        llm_client
    )
    
    return {
        "id": message.get("id"),
        "analisis": {
            "sentimiento": sentimiento,
            "temas": categorias.get("categorias", []),
            "relevancia_marketing": relevancia,
            "categoria_sugerida": _sugerir_categoria(sentimiento, categorias, relevancia)
        }
    }

def _sugerir_categoria(sentimiento, categorias, relevancia):
    """Sugiere qué tipo de activo generar basándose en el análisis."""
    if sentimiento["etiqueta"] in ["muy_positivo", "positivo"] and relevancia["score"] > 0.7:
        return "caso_exito"
    elif any(c["nombre"] == "duda_tecnica" for c in categorias.get("categorias", [])):
        return "faq_tip"
    elif sentimiento["etiqueta"] == "negativo":
        return "alerta_sentimiento"
    else:
        return "newsletter_highlight"
```

## 🧪 Cómo testearlo
```python
# tests/test_analysis.py
from unittest.mock import Mock, MagicMock
from src.analysis.sentiment import analyze_sentiment
from src.analysis.orchestrator import full_analysis

def test_sentiment_positive():
    mock_llm = Mock()
    mock_llm.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"sentiment": "muy_positivo", "score": 0.95, "confidence": 0.9}'))]
    )
    
    result = analyze_sentiment("¡Quede seleccionada para el trabajo!", mock_llm)
    assert result["etiqueta"] == "muy_positivo"
    assert result["score"] > 0.8

def test_full_analysis():
    mock_llm = Mock()
    # Mock para cada llamada (sentiment, categorization, relevance)
    mock_llm.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='{"sentiment": "positivo", "score": 0.85}'))]),
        Mock(choices=[Mock(message=Mock(content='{"categorias": [{"nombre": "contratacion_logro"}]}'))]),
        Mock(choices=[Mock(message=Mock(content='{"promedio_ponderado": 0.9}'))]),
    ]
    
    message = {"id": "1", "texto": "Me contrataron!", "canal": "#logros"}
    result = full_analysis(message, mock_llm)
    assert result["analisis"]["categoria_sugerida"] == "caso_exito"
```

## ⚠️ Errores comunes
| Error | Causa | Solución |
|-------|-------|----------|
| LLM retorna texto en vez de JSON | Prompt no especifica formato | Agregar `Responde SOLO en JSON válido` |
| Score negativo o > 1 | LLM inventa rangos | Agregar `El score debe ser un float entre 0 y 1` |
| Rate limit del LLM | Demasiadas llamadas simultáneas | Usar `time.sleep(1)` o cola con `asyncio` |
| Respuesta vacía | LLM no entiende el mensaje | Agregar few-shot examples en el prompt |

---

# 3️⃣ MÓDULO: PROMPTS

> **Responsable:** Data Scientists (2 y 3)
> **Rama:** `feat/prompts`

## 🎯 Qué hace
Contiene todos los system prompts organizados por función. Es la "caja de herramientas" de prompts del proyecto.

## 📁 Estructura
```
src/prompts/
├── __init__.py
├── sentiment_prompts.py      ← Para análisis de sentimiento
├── categorization_prompts.py ← Para categorización
├── relevance_prompts.py      ← Para puntuación
├── linkedin_prompts.py       ← Para posts de LinkedIn
├── newsletter_prompts.py     ← Para newsletters
├── testimonial_prompts.py    ← Para testimonios
├── faq_prompts.py            ← Para FAQ/Tips
└── templates.py              ← Funciones helper para armar prompts
```

## 🔑 Ejemplos de prompts clave

### `sentiment_prompts.py`
```python
SENTIMENT_SYSTEM_PROMPT = """Eres un experto en análisis de sentimiento de comunidades tecnológicas.

Tu tarea es analizar mensajes de comunidades de aprendizaje (Discord, Slack, foros) y determinar el sentimiento.

## Categorías de sentimiento:
- muy_positivo: Entusiasmo extremo, celebración, logros grandes (score: 0.8-1.0)
- positivo: Satisfacción, agradecimiento, interés (score: 0.6-0.79)
- neutral: Información pura, duda sin carga emocional (score: 0.4-0.59)
- negativo: Frustración, queja, decepción (score: 0.2-0.39)
- muy_negativo: Enfado fuerte, abandono, experiencia terrible (score: 0.0-0.19)

## Formato de respuesta (SOLO JSON):
{
  "sentiment": "muy_positivo|positivo|neutral|negativo|muy_negativo",
  "score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "emotion_detected": "alegría|orgullo|frustración|confusión|neutral",
  "keywords": ["palabra1", "palabra2"]
}

## Ejemplos:

Mensaje: "¡Quede seleccionada para Dev Jr de IA! El proyecto de LangChain marco la diferencia"
Respuesta: {"sentiment": "muy_positivo", "score": 0.95, "confidence": 0.92, "emotion_detected": "orgullo", "keywords": ["seleccionada", "diferencia"]}

Mensaje: "No entiendo cómo usar OCI, el tutorial no me sirve"
Respuesta: {"sentiment": "negativo", "score": 0.3, "confidence": 0.85, "emotion_detected": "frustración", "keywords": ["no entiendo", "no me sirve"]}

Mensaje: "Alguien tiene un ejemplo de LangGraph con router?"
Respuesta: {"sentiment": "neutral", "score": 0.5, "confidence": 0.8, "emotion_detected": "neutral", "keywords": ["ejemplo", "router"]}
"""
```

### `linkedin_prompts.py`
```python
LINKEDIN_SYSTEM_PROMPT = """Eres un copywriter experto en LinkedIn, especializado en contenido tech y comunidades de desarrolladores.

## Tu estilo:
- Tono inspirador pero auténtico (no suena a corporate)
- Empezás con un gancho fuerte (primera línea = enganche)
- Usás emojis con moderación (1-3 por post)
- Cerrás con CTA (llamada a la acción)
- Hashtags relevantes al final (3-5 máximo)

## Estructura del post:
1. GANCHO: Primera línea que genera curiosidad
2. HISTORIA: Contexto breve del logro/testimonio
3. LECCIÓN: Qué podemos aprender
4. CTA: Pregunta o invitación a la comunidad
5. HASHTAGS: Tags relevantes

## Formato de respuesta:
{
  "titulo": "Título impactante del post",
  "copy": "El texto completo del post",
  "canal_recomendado": "LinkedIn Oficial",
  "potencial_engagement": "Alto|Medio|Bajo",
  "hashtags": ["#tag1", "#tag2"],
  "mejor_hora_publicacion": "Martes 9am-11am"
}

## Ejemplo de post generado:

Input: Estudiante consiguió empleo como Dev Jr de IA después de hacer proyecto con LangChain y OCI

Output:
{
  "titulo": "De la Comunidad al Primer Empleo: El poder de construir en público",
  "copy": "Nada nos llena más de orgullo que ver a nuestros talentos conquistando el mercado. 🚀

Mariana Souza acaba de ser contratada como Desarrolladora Junior de IA. ¿Su secreto? Un proyecto práctico con LangChain y Oracle Cloud Infrastructure que construyó durante la formación.

Historias como la de Mariana nos recuerdan que el camino no es solo aprender teoría — es construir, romper, arreglar y volver a construir.

¿Estás trabajando en tu portfolio? Contanos en los comentarios 👇

#TalentosTech #InteligenciaArtificial #OracleCloud",
  "canal_recomendado": "LinkedIn Oficial",
  "potencial_engagement": "Alto",
  "hashtags": ["#TalentosTech", "#InteligenciaArtificial", "#OracleCloud"],
  "mejor_hora_publicacion": "Martes 9am-11am"
}
"""
```

### `templates.py`
```python
def build_prompt(system_prompt: str, user_content: str, examples: list = None) -> list[dict]:
    """
    Construye el array de mensajes para el LLM.
    
    Args:
        system_prompt: El system prompt base
        user_content: El contenido del usuario
        examples: Lista de ejemplos few-shot (opcional)
    """
    messages = [{"role": "system", "content": system_prompt}]
    
    # Agregar ejemplos few-shot si existen
    if examples:
        for ex in examples:
            messages.append({"role": "user", "content": ex["input"]})
            messages.append({"role": "assistant", "content": ex["output"]})
    
    messages.append({"role": "user", "content": user_content})
    return messages

def build_analysis_prompt(text: str, context: dict = None) -> str:
    """Arma el prompt para análisis con contexto adicional."""
    base = f"Analiza el siguiente mensaje de la comunidad:\n\n{text}"
    if context:
        base += f"\n\nContexto adicional:\n- Canal: {context.get('canal', 'desconocido')}"
        base += f"\n- Autor: {context.get('autor', 'desconocido')}"
        base += f"\n- Reacciones: {context.get('reacciones', 0)}"
    return base
```

## 🧪 Cómo testear prompts
```python
# tests/test_prompts.py
from src.prompts.templates import build_prompt
from src.prompts.sentiment_prompts import SENTIMENT_SYSTEM_PROMPT

def test_prompt_structure():
    messages = build_prompt(SENTIMENT_SYSTEM_PROMPT, "Test message")
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert "Test message" in messages[-1]["content"]

def test_prompt_with_examples():
    examples = [{"input": "Hola", "output": "Hola!"}]
    messages = build_prompt(SENTIMENT_SYSTEM_PROMPT, "Test", examples)
    assert len(messages) == 4  # system + example_user + example_assistant + user
```

---

# 4️⃣ MÓDULO: ORCHESTRATION

> **Responsable:** Software Engineer
> **Rama:** `feat/orchestration`

## 🎯 Qué hace
Conecta todos los módulos en un flujo secuencial o paralelo. Es el "director de orquesta" que decide qué módulo se ejecuta cuándo y cómo.

## 📥 Entrada
```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacciones": [...]
}
```

## 📤 Salida
```json
{
  "status": "exito",
  "resumen_comunidad": {...},
  "activos_distribucion_generados": {...},
  "almacenamiento_oci": {...}
}
```

## 🛠️ Tecnologías
- Python 3.10+
- Opción A: `langgraph` (para workflows complejos)
- Opción B: Python puro con funciones async
- Opción C: n8n (visual, pero menos flexible)

## 📁 Estructura
```
src/orchestration/
├── __init__.py
├── pipeline.py       ← Pipeline principal
├── router.py         ← Bifurcación condicional
├── async_queue.py    ← Cola asíncrona (opcional)
└── state.py          ← Estado del pipeline
```

## 🔑 Funciones clave

### `pipeline.py`
```python
import asyncio
from src.ingest.normalizer import normalize_batch
from src.analysis.orchestrator import full_analysis
from src.generators.linkedin_generator import generate_linkedin_post
from src.generators.newsletter_generator import generate_newsletter
from src.oci.persistence import save_assets_to_oci

class CommunityPulsePipeline:
    """Pipeline principal del sistema Community Pulse."""
    
    def __init__(self, llm_client, oci_client):
        self.llm = llm_client
        self.oci = oci_client
        self.router = ContentRouter()
    
    async def process(self, input_data: dict) -> dict:
        """
        Procesa un lote de interacciones de la comunidad.
        
        Flujo:
        1. Normalizar mensajes
        2. Analizar cada mensaje (sentimiento + categorías + relevancia)
        3. Routear según categoría
        4. Generar activos de marketing
        5. Guardar en OCI
        6. Retornar respuesta estructurada
        """
        
        # Paso 1: Normalizar
        messages = normalize_batch(
            input_data.get("interacciones", []),
            input_data.get("origen_comunidad", "discord")
        )
        
        # Paso 2: Analizar (paralelo para velocidad)
        analyses = await asyncio.gather(*[
            full_analysis(msg, self.llm) for msg in messages
        ])
        
        # Paso 3: Routear y generar activos
        assets = {}
        for analysis in analyses:
            category = analysis["analisis"]["categoria_sugerida"]
            generators = self.router.get_generators(category)
            
            for gen_func in generators:
                asset = await gen_func(analysis, self.llm)
                assets[asset["tipo"]] = asset
        
        # Paso 4: Empaquetar y guardar en OCI
        package = self._build_package(input_data, analyses, assets)
        oci_result = await save_assets_to_oci(self.oci, package)
        
        # Paso 5: Retornar respuesta
        return self._build_response(analyses, assets, oci_result)
    
    def _build_package(self, input_data, analyses, assets):
        """Empaqueta todo para OCI."""
        return {
            "periodo": input_data.get("periodo_referencia"),
            "origen": input_data.get("origen_comunidad"),
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "resumen": {
                "total_procesados": len(analyses),
                "sentimiento_predominante": self._get_predominant_sentiment(analyses),
                "temas_principales": self._get_main_topics(analyses),
            },
            "activos": assets,
        }
    
    def _get_predominant_sentiment(self, analyses):
        """Retorna el sentimiento más frecuente."""
        from collections import Counter
        sentiments = [a["analisis"]["sentimiento"]["etiqueta"] for a in analyses]
        return Counter(sentiments).most_common(1)[0][0]
    
    def _get_main_topics(self, analyses):
        """Retorna los temas más relevantes."""
        all_topics = []
        for a in analyses:
            all_topics.extend(a["analisis"].get("temas", []))
        from collections import Counter
        return [t for t, _ in Counter(all_topics).most_common(3)]
```

### `router.py`
```python
from src.generators.linkedin_generator import generate_linkedin_post
from src.generators.newsletter_generator import generate_newsletter
from src.generators.testimonial_generator import generate_testimonial
from src.generators.faq_generator import generate_faq_tip

class ContentRouter:
    """Decide qué generar según la categoría del mensaje."""
    
    # Mapa de categoría → generadores
    ROUTE_MAP = {
        "caso_exito": [
            generate_linkedin_post,
            generate_testimonial,
        ],
        "faq_tip": [
            generate_faq_tip,
            generate_newsletter,  # Sección "Tip de la semana"
        ],
        "newsletter_highlight": [
            generate_newsletter,
        ],
        "alerta_sentimiento": [],  # No genera activo, solo alerta
    }
    
    def get_generators(self, category: str) -> list:
        """Retorna la lista de generadores para una categoría."""
        generators = self.ROUTE_MAP.get(category, [])
        if not generators:
            # Fallback: siempre generar para newsletter
            return [generate_newsletter]
        return generators
```

## 🧪 Cómo testearlo
```python
# tests/test_orchestration.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.orchestration.pipeline import CommunityPulsePipeline

@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    mock_llm = Mock()
    mock_oci = AsyncMock()
    
    pipeline = CommunityPulsePipeline(mock_llm, mock_oci)
    
    input_data = {
        "origen_comunidad": "Discord",
        "periodo_referencia": "Semana_04",
        "interacciones": [
            {"autor": "Test", "canal": "#logros", "texto": "Me contrataron!"}
        ]
    }
    
    result = await pipeline.process(input_data)
    assert result["status"] == "exito"
    assert "activos" in result
```

---

# 5️⃣ MÓDULO: GENERATORS

> **Responsable:** Software Engineer + Data Scientists
> **Rama:** `feat/generators`

## 🎯 Qué hace
Genera activos de marketing específicos para cada canal. Cada generador tiene su lógica y prompts específicos.

## 📁 Estructura
```
src/generators/
├── __init__.py
├── linkedin_generator.py     ← Posts de LinkedIn
├── newsletter_generator.py   ← Resúmenes semanales
├── testimonial_generator.py  ← Casos de éxito
├── faq_generator.py          ← FAQ y Tips
└── image_generator.py        ← Banners (opcional)
```

## 🔑 Ejemplo: LinkedIn Generator

### `linkedin_generator.py`
```python
from src.prompts.linkedin_prompts import LINKEDIN_SYSTEM_PROMPT
from src.prompts.templates import build_prompt

async def generate_linkedin_post(analysis: dict, llm_client) -> dict:
    """
    Genera un post de LinkedIn a partir del análisis de un mensaje.
    
    Args:
        analysis: Resultado del análisis completo del mensaje
        llm_client: Cliente del LLM
    
    Returns:
        dict con el post generado
    """
    message_text = analysis.get("texto_original", "")
    sentiment = analysis["analisis"]["sentimiento"]["etiqueta"]
    topics = analysis["analisis"]["temas"]
    
    user_prompt = f"""Genera un post de LinkedIn basado en este mensaje de la comunidad:

Mensaje original: {message_text}
Sentimiento detectado: {sentiment}
Temas relevantes: {topics}

El post debe:
1. Tener un gancho fuerte en la primera línea
2. Contar la historia de forma inspiradora
3. Incluir un call-to-action
4. Tener 3-5 hashtags relevantes
5. Máximo 1300 caracteres (límite de LinkedIn)
"""
    
    messages = build_prompt(LINKEDIN_SYSTEM_PROMPT, user_prompt)
    
    response = await llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "tipo": "post_linkedin",
        "titulo": result.get("titulo", ""),
        "copy": result.get("copy", ""),
        "canal_recomendado": "LinkedIn Oficial",
        "potencial_engagement": result.get("potencial_engagement", "Medio"),
        "hashtags": result.get("hashtags", []),
    }
```

### `newsletter_generator.py`
```python
from src.prompts.templates import build_prompt

async def generate_newsletter(analysis: dict, llm_client) -> dict:
    """Genera una sección de newsletter semanal."""
    
    prompt = f"""Crea una sección de "Destaque de la Semana" para newsletter:

Mensaje: {analysis.get('texto_original')}
Tema: {analysis['analisis']['temas']}
Relevancia: {analysis['analisis']['relevancia_marketing']['score']}

Formato:
- Titular (máx 60 chars)
- Resumen ejecutivo (2-3 oraciones)
- Quote del miembro (si aplica)
- Enlace sugerido (placeholder)
"""
    
    response = await llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un editor de newsletters tech."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "tipo": "newsletter_highlight",
        "seccion": "Destaque de la Semana",
        "titular": result.get("titular", ""),
        "resumen": result.get("resumen", ""),
        "quote": result.get("quote", ""),
    }
```

### `testimonial_generator.py`
```python
async def generate_testimonial(analysis: dict, llm_client) -> dict:
    """Genera un caso de éxito/testimonio formateado."""
    
    prompt = f"""Crea un testimonio formateado para marketing:

Mensaje original: {analysis.get('texto_original')}
Autor: {analysis.get('autor')}
Sentimiento: {analysis['analisis']['sentimiento']['etiqueta']}

Formato:
- Título del caso
- Narrativa (3-4 oraciones)
- Resultado concreto
- CTA para la comunidad
"""
    
    response = await llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un storyteller de casos de éxito tech."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "tipo": "caso_exito",
        "titulo": result.get("titulo", ""),
        "narrativa": result.get("narrativa", ""),
        "resultado": result.get("resultado", ""),
        "cta": result.get("cta", ""),
    }
```

### `faq_generator.py`
```python
async def generate_faq_tip(analysis: dict, llm_client) -> dict:
    """Genera un FAQ o Tip rápido a partir de una duda frecuente."""
    
    prompt = f"""Crea un "Tip Rápido" para la comunidad:

Duda original: {analysis.get('texto_original')}
Tema: {analysis['analisis']['temas']}

Formato:
- Título del tip
- Explicación breve (3-5 oraciones)
- Ejemplo práctico (si aplica)
- Referencia a documentación oficial
"""
    
    response = await llm_client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Eres un mentor técnico que explica de forma simple."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    
    return {
        "tipo": "faq_tip",
        "tema": result.get("tema", ""),
        "titulo_tip": result.get("titulo", ""),
        "explicacion": result.get("explicacion", ""),
        "ejemplo": result.get("ejemplo", ""),
        "origen": f"Duda de {analysis.get('autor', 'miembro de la comunidad')}",
    }
```

---

# 6️⃣ MÓDULO: OCI (Oracle Cloud Infrastructure)

> **Responsable:** Backend Developer
> **Rama:** `feat/oci-storage`

## 🎯 Qué hace
Conecta con Oracle Cloud para almacenar los paquetes de activos generados. Es el componente de persistencia en la nube.

## 📁 Estructura
```
src/oci/
├── __init__.py
├── oci_client.py      ← Conexión con OCI
├── storage.py         ← Upload/download de archivos
├── persistence.py     ← Guarda resultados del pipeline
└── config.py          ← Configuración de credenciales
```

## 🔑 Funciones clave

### `oci_client.py`
```python
import oci
from src.oci.config import OCI_CONFIG

class OCIStorageClient:
    """Cliente para OCI Object Storage."""
    
    def __init__(self):
        # Autenticación con config file o instance principal
        self.config = OCI_CONFIG
        self.object_storage_client = oci.object_storage.ObjectStorageClient(self.config)
        self.namespace = self.object_storage_client.get_namespace().data
        self.bucket_name = "community-pulse-activos-marketing"
    
    def create_bucket_if_not_exists(self):
        """Crea el bucket si no existe."""
        try:
            self.object_storage_client.get_bucket(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name
            )
        except oci.exceptions.ServiceError:
            # Bucket no existe, crearlo
            create_bucket_details = oci.object_storage.models.CreateBucketDetails(
                name=self.bucket_name,
                compartment_id=self.config["compartment_id"],
                public_access_type="NoPublicAccess"
            )
            self.object_storage_client.create_bucket(
                namespace_name=self.namespace,
                create_bucket_details=create_bucket_details
            )
            print(f"✅ Bucket '{self.bucket_name}' creado exitosamente")
```

### `storage.py`
```python
import json
from datetime import datetime

class OCIStorage:
    """Funciones de almacenamiento en OCI."""
    
    def __init__(self, client: OCIStorageClient):
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
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        
        response = self.client.object_storage_client.put_object(
            namespace_name=self.client.namespace,
            bucket_name=self.client.bucket_name,
            object_name=path,
            put_object_body=json_bytes,
            content_type="application/json"
        )
        
        return {
            "status": "guardado_con_exito",
            "bucket": self.client.bucket_name,
            "ruta_objeto": path,
            "tamaño_bytes": len(json_bytes)
        }
    
    def generate_path(self, periodo: str, tipo: str = "paquete") -> str:
        """Genera la ruta del objeto basada en el período."""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"activos/{periodo}/{tipo}-{timestamp}.json"
```

### `persistence.py`
```python
from src.oci.storage import OCIStorage

async def save_assets_to_oci(oci_storage: OCIStorage, package: dict) -> dict:
    """
    Guarda el paquete completo de activos en OCI.
    
    Estructura del bucket:
    community-pulse-activos-marketing/
    └── activos/
        └── 2026-semana-04/
            ├── paquete-completo.json    ← Todo junto
            ├── post-linkedin.json       ← Solo LinkedIn
            ├── newsletter.json          ← Solo Newsletter
            └── analisis.json            ← Solo análisis
    """
    periodo = package.get("periodo", "sin_periodo")
    
    # Guardar paquete completo
    path_completo = oci_storage.generate_path(periodo, "paquete-completo")
    result_completo = oci_storage.upload_json(package, path_completo)
    
    # Guardar activos individuales
    activos = package.get("activos", {})
    resultados_individuales = []
    
    for tipo, contenido in activos.items():
        path_individual = oci_storage.generate_path(periodo, tipo)
        result = oci_storage.upload_json(contenido, path_individual)
        resultados_individuales.append(result)
    
    return {
        "bucket": oci_storage.client.bucket_name,
        "paquete_completo": result_completo,
        "activos_individuales": resultados_individuales,
        "total_archivos": 1 + len(resultados_individuales)
    }
```

### `config.py`
```python
import os

# ⚠️ NUNCA commitear credenciales reales
# Usar variables de entorno o OCI config file

OCI_CONFIG = {
    "user": os.getenv("OCI_USER_ID"),
    "key_file": os.getenv("OCI_KEY_FILE_PATH", "~/.oci/oci_api_key.pem"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION", "sa-saopaulo-1"),  # Brasil
    "compartment_id": os.getenv("OCI_COMPARTMENT_ID"),
}

# Para testing local con mock
OCI_MOCK_CONFIG = {
    "user": "mock",
    "key_file": "mock",
    "fingerprint": "mock",
    "tenancy": "mock",
    "region": "mock",
    "compartment_id": "mock",
}
```

## 🧪 Cómo testearlo
```python
# tests/test_oci.py
from unittest.mock import Mock, patch
from src.oci.storage import OCIStorage

def test_upload_json():
    mock_client = Mock()
    mock_client.object_storage_client.put_object.return_value = Mock(status=200)
    mock_client.namespace = "test"
    mock_client.bucket_name = "test-bucket"
    
    storage = OCIStorage(mock_client)
    result = storage.upload_json({"test": "data"}, "test/file.json")
    
    assert result["status"] == "guardado_con_exito"
    mock_client.object_storage_client.put_object.assert_called_once()

def test_generate_path():
    mock_client = Mock()
    storage = OCIStorage(mock_client)
    path = storage.generate_path("2026-semana-04")
    assert "activos/2026-semana-04/" in path
```

---

# 7️⃣ MÓDULO: INTERFACE (Streamlit)

> **Responsable:** Software Engineer
> **Rama:** `feat/interface`

## 🎯 Qué hace
Interfaz web para que el equipo de marketing pueda:
- Ver los activos generados
- Editar contenido antes de publicar
- Aprobar o rechazar publicaciones
- Visualizar métricas de la comunidad

## 📁 Estructura
```
src/interface/
├── __init__.py
├── app.py               ← Entry point principal
├── pages/
│   ├── 1_dashboard.py   ← Métricas y sentimiento
│   ├── 2_curaduria.py   ← Panel de curaduría
│   ├── 3_generar.py     ← Generar nuevos activos
│   └── 4_config.py      ← Configuración
├── components/
│   ├── post_card.py     ← Tarjeta de post para revisar
│   ├── sentiment_chart.py ← Gráfico de sentimiento
│   └── metrics.py       ← Métricas de la comunidad
└── styles/
    └── main.css         ← Estilos personalizados
```

## 🔑 Código principal

### `app.py`
```python
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Community Pulse",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar con navegación
st.sidebar.title("🚀 Community Pulse")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navegación",
    ["📊 Dashboard", "✍️ Curaduría", "⚡ Generar", "⚙️ Configuración"]
)

# Renderizar página seleccionada
if page == "📊 Dashboard":
    from pages.dashboard import render_dashboard
    render_dashboard()
elif page == "✍️ Curaduría":
    from pages.curaduria import render_curaduria
    render_curaduria()
elif page == "⚡ Generar":
    from pages.generar import render_generar
    render_generar()
elif page == "⚙️ Configuración":
    from pages.config import render_config
    render_config()
```

### `pages/2_curaduria.py`
```python
import streamlit as st
from src.generators.linkedin_generator import generate_linkedin_post

def render_curaduria():
    st.title("✍️ Panel de Curaduría")
    st.markdown("Revisa, edita y aprueba los activos generados por la IA.")
    
    # Cargar activos pendientes (desde OCI o session state)
    activos = st.session_state.get("activos_pendientes", [])
    
    if not activos:
        st.info("No hay activos pendientes de revisión. Generá nuevos en la pestaña 'Generar'.")
        return
    
    for idx, activo in enumerate(activos):
        with st.expander(f"📝 {activo.get('titulo', 'Sin título')} - {activo.get('tipo', '')}", expanded=True):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Editar título
                titulo = st.text_input("Título", activo.get("titulo", ""), key=f"titulo_{idx}")
                
                # Editar contenido
                copy = st.text_area(
                    "Contenido", 
                    activo.get("copy", activo.get("resumen", "")), 
                    height=200,
                    key=f"copy_{idx}"
                )
                
                # Hashtags
                hashtags = st.text_input(
                    "Hashtags", 
                    " ".join(activo.get("hashtags", [])),
                    key=f"tags_{idx}"
                )
            
            with col2:
                st.markdown("**Metadata:**")
                st.write(f"Canal: {activo.get('canal_recomendado', 'N/A')}")
                st.write(f"Engagement: {activo.get('potencial_engagement', 'N/A')}")
                st.write(f"Tipo: {activo.get('tipo', 'N/A')}")
                
                # Preview
                if st.button("👁️ Preview", key=f"preview_{idx}"):
                    st.markdown("---")
                    st.markdown(f"### {titulo}")
                    st.markdown(copy)
                    st.markdown(hashtags)
            
            # Acciones
            col_approve, col_reject, col_edit = st.columns(3)
            
            with col_approve:
                if st.button("✅ Aprobar", key=f"approve_{idx}"):
                    st.success(f"Publicación '{titulo}' aprobada!")
                    # Mover a aprobados
                    
            with col_reject:
                if st.button("❌ Rechazar", key=f"reject_{idx}"):
                    st.warning(f"Publicación '{titulo}' rechazada.")
                    
            with col_edit:
                if st.button("🔄 Regenerar", key=f"regen_{idx}"):
                    st.info("Regenerando contenido...")
                    # Llamar al generador nuevamente
```

### `pages/1_dashboard.py`
```python
import streamlit as st
import pandas as pd

def render_dashboard():
    st.title("📊 Dashboard de la Comunidad")
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Mensajes procesados", "1,234", "+12%")
    with col2:
        st.metric("Sentimiento positivo", "68%", "+5%")
    with col3:
        st.metric("Activos generados", "47", "+8")
    with col4:
        st.metric("Tasa de aprobación", "89%", "+3%")
    
    st.markdown("---")
    
    # Gráfico de sentimiento
    col_chart, col_topics = st.columns(2)
    
    with col_chart:
        st.subheader("Distribución de Sentimiento")
        # Datos de ejemplo
        sentiment_data = pd.DataFrame({
            "Categoría": ["Muy Positivo", "Positivo", "Neutral", "Negativo", "Muy Negativo"],
            "Porcentaje": [25, 43, 20, 8, 4]
        })
        st.bar_chart(sentiment_data.set_index("Categoría"))
    
    with col_topics:
        st.subheader("Temas Principales")
        topics_data = pd.DataFrame({
            "Tema": ["LangChain", "OCI", "Portfolios", "Empleo", "Python"],
            "Frecuencia": [45, 38, 35, 32, 28]
        })
        st.bar_chart(topics_data.set_index("Tema"))
    
    # Últimos activos generados
    st.subheader("📝 Últimos Activos Generados")
    st.dataframe({
        "Fecha": ["2026-09-10", "2026-09-10", "2026-09-09"],
        "Tipo": ["LinkedIn", "Newsletter", "FAQ"],
        "Título": ["De la comunidad al empleo", "Highlights semana 4", "Tip: LangGraph Router"],
        "Estado": ["✅ Aprobado", "⏳ Pendiente", "✅ Aprobado"],
    })
```

## 🧪 Cómo testearlo
```python
# Streamlit no tiene testing unitario tradicional
# Usar st.testing o verificar que los componentes renderizan

def test_dashboard_loads():
    """Verifica que el dashboard carga sin errores."""
    # No se puede testear directamente con pytest
    # Verificar importación
    from src.interface.pages.dashboard import render_dashboard
    assert callable(render_dashboard)

# Para testing visual: usar Streamlit AppTest (experimental)
# from streamlit.testing.v1 import AppTest
# at = AppTest.from_file("src/interface/app.py")
# at.run()
# assert not at.exception
```

---

## 📋 Resumen de Módulos

| Módulo | Responsable | Rama | Dependencias |
|--------|-------------|------|--------------|
| 1. Ingest | SE + DA | `feat/ingesta` | Ninguna |
| 2. Analysis | DS (3) | `feat/analysis` | Prompts |
| 3. Prompts | DS (2,3) | `feat/prompts` | Ninguna |
| 4. Orchestration | SE | `feat/orchestration` | Ingest + Analysis + Generators |
| 5. Generators | SE + DS | `feat/generators` | Prompts |
| 6. OCI | BE | `feat/oci-storage` | Config OCI |
| 7. Interface | SE | `feat/interface` | Orchestration |

---

*Guía creada para el equipo Community Pulse — Oracle ONE Hackathon G10*
