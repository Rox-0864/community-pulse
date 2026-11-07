# 🧠 MODULO DIFERENCIAL: TOMA DE DECISIONES INTELIGENTES

> **Componente estrella del proyecto — lo que separa un MVP estándar de un sistema completo**
>
> **Responsables:** Tech Lead (diseño) + Data Scientists (lógica + prompts) + Backend (integración OCI)

---

## 🎯 ¿Qué agrega este módulo?

El PDF exige: análisis → generación de activos → almacenamiento. Eso es el MVP BÁSICO.

Este módulo agrega la **CAPA DE DECISIÓN** que transforma el proyecto de "generador de posts" a **"sistema de inteligencia de comunidad"**:

| Señal detectada | Decisión automática | Acción resultante |
|-----------------|---------------------|-------------------|
| 📉 Miembro con sentimiento negativo recurrente | **Alerta de riesgo** | Notificación al community manager + sugerencia de intervención |
| ❓ Misma duda técnica aparece 3+ veces | **Derivación a mentoría** | FAQ generado + entrada en cola de mentoría |
| 💡 Feedback positivo repetido sobre un curso | **Destaque para newsletter** | Sección "Highlight del mes" + evaluar caso de éxito completo |
| 🏆 Testimonio con relevancia > 0.85 | **Prioridad alta de publicación** | Post LinkedIn marcado como "publicar hoy" |
| 😠 Queja sobre un curso/feature | **Escalamiento a producto** | Ticket interno + alerta al equipo |

---

## 📁 Estructura del módulo

```
src/decisions/
├── __init__.py
├── engine.py              ← Motor principal de decisiones
├── member_risk.py         ← Detector de miembros en riesgo
├── recurring_topics.py    ← Detector de dudas recurrentes
├── escalation.py          ← Reglas de escalamiento
├── notifications.py       ← Genera notificaciones/alertas
└── prompts.py             ← Prompts para el LLM de decisiones

otros pipes (afectados):
├── src/analysis/orchestrator.py   ← Ahora retorna datos para decisiones
└── src/oci/persistence.py         ← Ahora guarda también decisiones
```

---

## 1️⃣ ENGINE.PY — El cerebro que decide

### 🎯 Qué hace
Recibe el análisis de todos los mensajes del lote y **decide qué acciones ejecutar** basándose en reglas + señales del LLM.

### 📥 Entrada
```json
{
  "periodo_referencia": "Semana_04",
  "mensajes_analizados": [
    {
      "id": "msg_001",
      "autor": "Mariana Souza",
      "sentimiento": {"etiqueta": "muy_positivo", "score": 0.95},
      "temas": ["contratacion", "logro"],
      "relevancia": 0.92,
      "categoria_sugerida": "caso_exito"
    },
    {
      "id": "msg_002",
      "autor": "Lucas Albuquerque",
      "sentimiento": {"etiqueta": "neutral", "score": 0.5},
      "temas": ["langgraph", "duda_tecnica"],
      "relevancia": 0.45,
      "categoria_sugerida": "faq_tip"
    },
    {
      "id": "msg_003",
      "autor": "João Pereira",
      "sentimiento": {"etiqueta": "negativo", "score": 0.25},
      "temas": ["oci", "proyecto_bloqueado"],
      "relevancia": 0.6,
      "categoria_sugerida": "alerta_sentimiento"
    }
  ]
}
```

### 📤 Salida
```json
{
  "acciones_recomendadas": [
    {
      "tipo": "publicar_prioritario",
      "mensaje_id": "msg_001",
      "razon": "Testimonio de éxito con relevancia 0.92",
      "prioridad": "ALTA",
      "activo_sugerido": "post_linkedin"
    },
    {
      "tipo": "derivar_mentoria",
      "mensaje_id": "msg_002",
      "razon": "Duda técnica recurrente sobre LangGraph",
      "mentor_sugerido": "especialista_langgraph",
      "activo_sugerido": "faq_tip"
    },
    {
      "tipo": "alerta_miembro",
      "mensaje_id": "msg_003",
      "autor": "João Pereira",
      "nivel_riesgo": 0.78,
      "razon": "Sentimiento negativo persistente + problema bloqueante",
      "accion_sugerida": "contactar_individualmente",
      "activo_sugerido": "ninguno"
    }
  ],
  "resumen_ejecutivo": {
    "miembros_en_riesgo": 1,
    "dudas_recurrentes": 1,
    "testimonios_destacables": 1,
    "acciones_automaticas": 3
  }
}
```

### 🔑 Código

```python
# src/decisions/engine.py
from src.decisions.member_risk import MemberRiskDetector
from src.decisions.recurring_topics import RecurringTopicsDetector
from src.decisions.escalation import EscalationRules

class DecisionEngine:
    """Motor principal de decisiones de Community Pulse."""
    
    def __init__(self, llm_client, historial: dict = None):
        self.llm = llm_client
        self.historial = historial or {
            "mensajes_semanas_previas": [],
            "dudas_resueltas": [],
            "miembros_tracking": {}
        }
        self.risk_detector = MemberRiskDetector(llm_client, self.historial)
        self.recurring_detector = RecurringTopicsDetector()
        self.escalation = EscalationRules()
    
    def process_batch(self, batch_analysis: dict) -> dict:
        """
        Procesa un lote de mensajes analizados y decide acciones.
        
        Flujo de decisión para cada mensaje:
        1. ¿Es un testimonio de alto valor? → publicar prioritario
        2. ¿Es una duda técnica recurrente? → derivar a mentoría + FAQ
        3. ¿El autor tiene sentimiento negativo persistente? → alerta
        4. ¿Es feedback sobre el producto? → escalar o destacar
        """
        acciones = []
        autores_en_batch = {}
        
        # Agrupar mensajes por autor para análisis de riesgo
        for msg in batch_analysis.get("mensajes_analizados", []):
            autor = msg.get("autor", "anónimo")
            autores_en_batch.setdefault(autor, []).append(msg)
        
        # Decisión por mensaje
        for msg in batch_analysis.get("mensajes_analizados", []):
            accion = self._decidir_por_mensaje(msg)
            if accion:
                acciones.append(accion)
        
        # Análisis de riesgo por autor (requiere historial)
        for autor, mensajes_autor in autores_en_batch.items():
            riesgo = self.risk_detector.evaluate_author(autor, mensajes_autor)
            if riesgo["nivel_riesgo"] > 0.6:
                acciones.append({
                    "tipo": "alerta_miembro",
                    "autor": autor,
                    "nivel_riesgo": riesgo["nivel_riesgo"],
                    "razon": riesgo["razon"],
                    "accion_sugerida": riesgo["accion_sugerida"]
                })
        
        # Detección de dudas recurrentes (buscar en historial)
        dudas = self.recurring_detector.detect(
            batch_analysis.get("mensajes_analizados", []),
            self.historial.get("dudas_resueltas", [])
        )
        for duda in dudas:
            acciones.append({
                "tipo": "derivar_mentoria",
                "tema": duda["tema"],
                "veces_detectada": duda["veces_detectada"],
                "mentor_sugerido": duda["mentor_sugerido"],
                "activo_sugerido": "faq_tip"
            })
        
        # Construir resumen ejecutivo
        resumen = self._build_resumen(acciones)
        
        return {
            "acciones_recomendadas": acciones,
            "resumen_ejecutivo": resumen
        }
    
    def _decidir_por_mensaje(self, msg: dict) -> dict | None:
        """Reglas de decisión para un mensaje individual."""
        # R1: Testimonio de alto valor → publicar prioritario
        if (msg.get("categoria_sugerida") == "caso_exito" and
            msg.get("relevancia", 0) > 0.8):
            return {
                "tipo": "publicar_prioritario",
                "mensaje_id": msg.get("id"),
                "razon": f"Testimonio con relevancia {msg.get('relevancia', 0):.2f}",
                "prioridad": "ALTA",
                "activo_sugerido": "post_linkedin"
            }
        
        # R2: Duda técnica → FAQ (se combina con detección recurrente)
        if msg.get("categoria_sugerida") == "faq_tip":
            return {
                "tipo": "generar_faq",
                "mensaje_id": msg.get("id"),
                "razon": "Duda técnica identificada",
                "activo_sugerido": "faq_tip"
            }
        
        # R3: Sentimiento negativo fuerte → alerta de riesgo
        if msg.get("sentimiento", {}).get("etiqueta") in ["negativo", "muy_negativo"]:
            return {
                "tipo": "alerta_sentimiento_puntual",
                "mensaje_id": msg.get("id"),
                "razon": f"Sentimiento {msg.get('sentimiento', {}).get('etiqueta')} detectado",
                "accion_sugerida": "monitorear"
            }
        
        return None
    
    def _build_resumen(self, acciones: list[dict]) -> dict:
        """Construye el resumen ejecutivo para el dashboard."""
        from collections import Counter
        tipos = Counter(a["tipo"] for a in acciones)
        return {
            "miembros_en_riesgo": tipos.get("alerta_miembro", 0) + tipos.get("alerta_sentimiento_puntual", 0),
            "dudas_detectadas": tipos.get("generar_faq", 0) + tipos.get("derivar_mentoria", 0),
            "testimonios_destacables": tipos.get("publicar_prioritario", 0),
            "acciones_automaticas": len(acciones)
        }
```

---

## 2️⃣ MEMBER_RISK.PY — Detector de miembros en riesgo

### 🎯 Qué hace
Monitorea la **trayectoria de sentimiento de cada miembro** a lo largo del tiempo. Un miembro que era positivo y ahora es consistentemente negativo = **riesgo de abandono** (churn).

### 🔑 Código

```python
# src/decisions/member_risk.py
from src.decisions.prompts import RISK_ANALYSIS_PROMPT

class MemberRiskDetector:
    """Detecta miembros en riesgo de abandonar la comunidad."""
    
    # Umbrales de riesgo
    UMBRAL_RECIENTE_NEGATIVO = 2   # ≥2 mensajes negativos recientes
    UMBRAL_CAIDA_EMOCIONAL = -0.4  # caída de score ≥ 0.4 vs promedio histórico
    UMBRAL_ALERTA = 0.6            # nivel de riesgo para generar alerta
    
    def __init__(self, llm_client, historial: dict):
        self.llm = llm_client
        self.historial = historial
    
    def evaluate_author(self, autor: str, mensajes_lote: list[dict]) -> dict:
        """
        Evalúa el nivel de riesgo de abandonar la comunidad para un autor.
        
        Combina 3 señales:
        S1: Sentimiento promedio reciente del autor
        S2: Tendencia vs historial previo (¿está cayendo?)
        S3: Contenido de los mensajes (¿problemas bloqueantes?)
        """
        # S1: Sentimiento promedio del lote actual
        sentimiento_reciente = self._average_sentiment(mensajes_lote)
        
        # S2: Comparar con historial (si existe)
        historial_autor = self.historial.get("miembros_tracking", {}).get(autor, {})
        sentimiento_historico = historial_autor.get("sentimiento_promedio", 0.5)
        
        caida = sentimiento_historico - sentimiento_reciente
        
        # S3: Detectar señales de frustración en el texto
        frustacion = self._detect_frustration(mensajes_lote)
        
        # Calcular nivel de riesgo (0-1)
        nivel_riesgo = self._compute_risk_level(
            sentimiento_reciente,
            caida,
            frustacion
        )
        
        razon = self._build_reason(
            autor, sentimiento_reciente, caida, frustacion, nivel_riesgo
        )
        
        accion = "contactar_individualmente" if nivel_riesgo >= self.UMBRAL_ALERTA else "monitorear"
        
        return {
            "autor": autor,
            "nivel_riesgo": round(nivel_riesgo, 2),
            "razon": razon,
            "accion_sugerida": accion,
            "senales": {
                "sentimiento_reciente": round(sentimiento_reciente, 2),
                "caida_vs_historial": round(caida, 2),
                "frustracion_detectada": frustacion
            }
        }
    
    def _average_sentiment(self, mensajes: list[dict]) -> float:
        """Promedio de scores de sentimiento de los mensajes."""
        scores = [m.get("sentimiento", {}).get("score", 0.5) for m in mensajes]
        if not scores:
            return 0.5
        return sum(scores) / len(scores)
    
    def _detect_frustration(self, mensajes: list[dict]) -> bool:
        """Detecta palabras de frustración en los mensajes."""
        FRUSTRACION_KEYWORDS = [
            "no funciona", "no puedo", "error", "bug", "frustrado",
            "me rindo", "abandonar", "no entiendo", "no me sirve",
            "horrible", "terrible", "perdido", "trabado", "bloqueado"
        ]
        texto_completo = " ".join(m.get("texto", "").lower() for m in mensajes)
        return any(kw in texto_completo for kw in FRUSTRACION_KEYWORDS)
    
    def _compute_risk_level(self, sentimiento: float, caida: float, frustacion: bool) -> float:
        """Calcula el nivel de riesgo combinando las señales."""
        riesgo = 0.0
        
        # Peso 1: Sentimiento negativo (40%)
        riesgo += (1 - sentimiento) * 0.4
        
        # Peso 2: Caída vs historial (35%)
        if caida > 0:
            riesgo += min(caida, 1) * 0.35
        
        # Peso 3: Frustración explícita (25%)
        if frustacion:
            riesgo += 0.25
        
        return min(max(riesgo, 0), 1)
    
    def _build_reason(self, autor, sentimiento, caida, frustacion, nivel) -> str:
        """Construye una razón legible para la alerta."""
        razones = []
        if sentimiento < 0.4:
            razones.append(f"sentimiento promedio bajo ({sentimiento:.2f})")
        if caida > self.UMBRAL_CAIDA_EMOCIONAL:
            razones.append(f"caída emocional vs historial ({caida:.2f})")
        if frustacion:
            razones.append("señales de frustración en mensajes")
        
        texto = "; ".join(razones[:2])  # máx 2 razones para legibilidad
        return f"Alerta {autor}: {texto}" if razones else f"Monitoreo estándar para {autor}"
```

---

## 3️⃣ RECURRING_TOPICS.PY — Detector de dudas recurrentes

### 🎯 Qué hace
Detecta cuándo la MISMA duda técnica aparece repetidamente. Usa **embedding o hash de temas** para comparar.

### 🔑 Código

```python
# src/decisions/recurring_topics.py
from collections import Counter

class RecurringTopicsDetector:
    """Detecta dudas técnicas que se repiten en el tiempo."""
    
    UMBRAL_REPETICION = 3  # misma duda 3+ veces = recurrente
    
    def __init__(self, umbral: int = UMBRAL_REPETICION):
        self.umbral = umbral
    
    def detect(self, mensajes_lote: list[dict], dudas_historial: list[dict]) -> list[dict]:
        """
        Detecta dudas recurrentes combinando el lote actual con el historial.
        
        Estrategia:
        1. Extraer temas de los mensajes con categoría duda_tecnica
        2. Contar frecuencias en el lote actual
        3. Sumar con frecuencias del historial
        4. Temas con >= umbral = recurrente
        """
        # 1 y 2: Contar temas en el lote actual
        temas_lote = Counter()
        for msg in mensajes_lote:
            if msg.get("categoria_sugerida") == "faq_tip" or \
               "duda_tecnica" in msg.get("temas", []):
                for tema in msg.get("temas", []):
                    if isinstance(tema, str):
                        temas_lote[tema.lower()] += 1
        
        # 3: Sumar historial
        temas_historial = Counter()
        for duda in dudas_historial:
            temas_historial[duda.get("tema", "").lower()] = duda.get("veces", 1)
        
        temas_totales = temas_lote + temas_historial
        
        # 4: Filtrar recurrentes
        recurrentes = []
        for tema, veces in temas_totales.items():
            if veces >= self.umbral and tema:
                recurrentes.append({
                    "tema": tema,
                    "veces_detectada": veces,
                    "mentor_sugerido": self._suggest_mentor(tema),
                    "nivel_urgencia": "ALTO" if veces >= 5 else "MEDIO",
                    "accion": "generar_faq_y_derivar"
                })
        
        return recurrentes
    
    def _suggest_mentor(self, tema: str) -> str:
        """Sugiere qué especialista debería atender la duda."""
        AREAS = {
            "langgraph": "especialista_langgraph",
            "langchain": "especialista_langchain",
            "oci": "especialista_oracle_cloud",
            "oracle": "especialista_oracle_cloud",
            "python": "mentor_python",
            "prompt": "especialista_ia",
            "gemini": "especialista_ia",
            "streamlit": "especialista_frontend",
            "docker": "especialista_devops",
            "deploy": "especialista_devops",
        }
        
        for key, mentor in AREAS.items():
            if key in tema.lower():
                return mentor
        
        return "mentor_general"
```

---

## 4️⃣ ESCALATION.PY — Reglas de escalamiento

### 🎯 Qué hace
Clasifica el nivel de gravedad de las alertas y define qué acción tomar para cada nivel.

### 🔑 Código

```python
# src/decisions/escalation.py

class EscalationRules:
    """Reglas para escalar alertas según su gravedad."""
    
    NIVELES_ESCALAMIENTO = {
        "INFO": {
            "prioridad": 1,
            "tiempo_respuesta": "24 horas",
            "accion": "registrar_en_dashboard"
        },
        "MEDIO": {
            "prioridad": 2,
            "tiempo_respuesta": "4 horas",
            "accion": "notificar_community_manager"
        },
        "ALTO": {
            "prioridad": 3,
            "tiempo_respuesta": "1 hora",
            "accion": "notificar_team_lead + contactar_miembro"
        },
        "CRITICO": {
            "prioridad": 4,
            "tiempo_respuesta": "inmediato",
            "accion": "contacto_personal + revisión de caso + plan de retención"
        }
    }
    
    def classify(self, alerta: dict) -> dict:
        """
        Clasifica la gravedad de una alerta.
        
        Criterios:
        - nivel_riesgo > 0.85 o frustración + abandono → CRITICO
        - nivel_riesgo > 0.6 o queja de curso/feature → ALTO
        - nivel_riesgo > 0.4 o duda recurrente ≥5 → MEDIO
        - resto → INFO
        """
        nivel_riesgo = alerta.get("nivel_riesgo", 0)
        tipo = alerta.get("tipo", "")
        tema = alerta.get("tema", "").lower()
        
        # Criterios CRITICO
        if nivel_riesgo > 0.85:
            nivel = "CRITICO"
        elif nivel_riesgo > 0.6 or "queja" in tipo:
            nivel = "ALTO"
        elif nivel_riesgo > 0.4 or alerta.get("veces_detectada", 0) >= 5:
            nivel = "MEDIO"
        else:
            nivel = "INFO"
        
        reglas = self.NIVELES_ESCALAMIENTO[nivel]
        
        return {
            "nivel": nivel,
            "prioridad": reglas["prioridad"],
            "tiempo_respuesta": reglas["tiempo_respuesta"],
            "accion": reglas["accion"],
            "requiere_intervencion_humana": nivel in ["ALTO", "CRITICO"]
        }
```

---

## 5️⃣ NOTIFICATIONS.PY — Genera las alertas

### 🎯 Qué hace
Convierte las decisiones en **notificaciones accionables** que el community manager ve en el dashboard (o recibe por email/slack).

### 🔑 Código

```python
# src/decisions/notifications.py
from datetime import datetime

class NotificationBuilder:
    """Construye notificaciones legibles para humanos."""
    
    def build_member_alert(self, alerta: dict, escalamiento: dict) -> dict:
        """Notificación para miembro en riesgo."""
        return {
            "tipo_notificacion": "ALERTA_MIEMBRO",
            "gravedad": escalamiento["nivel"],
            "titulo": f"⚠️ Miembro en riesgo: {alerta['autor']}",
            "mensaje": f"""
Miembro {alerta['autor']} muestra señales de posible abandono.

Razón: {alerta['razon']}
Nivel de riesgo: {alerta['nivel_riesgo']:.0%}
Señales detectadas:
• Sentimiento reciente: {alerta['senales']['sentimiento_reciente']}
• Caída vs historial: {alerta['senales']['caida_vs_historial']}
• Frustración en mensajes: {'Sí' if alerta['senales']['frustracion_detectada'] else 'No'}

Acción requerida: {alerta['accion_sugerida']}
Tiempo de respuesta: {escalamiento['tiempo_respuesta']}
""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": "community_manager",
            "canal": "dashboard"
        }
    
    def build_mentorship_referral(self, duda: dict, escalamiento: dict) -> dict:
        """Notificación para derivación a mentoría."""
        return {
            "tipo_notificacion": "DERIVAR_MENTORIA",
            "gravedad": escalamiento["nivel"],
            "titulo": f"📚 Duda recurrente: {duda['tema']}",
            "mensaje": f"""
La siguiente duda apareció {duda['veces_detectada']} veces en la comunidad:
"{duda['tema']}"

Mentor sugerido: {duda['mentor_sugerido']}
Acción: {duda['accion']}

Se generó FAQ automático. Se sugiere revisión de mentor.
""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": duda["mentor_sugerido"],
            "canal": "dashboard"
        }
    
    def build_publication_priority(self, testimonio: dict) -> dict:
        """Notificación para publicación prioritaria."""
        return {
            "tipo_notificacion": "PUBLICAR_PRIORITARIO",
            "gravedad": "INFO",
            "titulo": "🚀 Testimonio listo para publicación",
            "mensaje": f"""
Un testimonio de alto valor está listo para publicar.

Razón: {testimonio['razon']}
Activo generado: {testimonio.get('activo_sugerido', 'post_linkedin')}
Canal recomendado: LinkedIn Oficial

Aprobación requerida en panel de curaduría.
""",
            "timestamp": datetime.now().isoformat(),
            "destinatario": "equipo_marketing",
            "canal": "dashboard"
        }
```

---

## 6️⃣ PROMPTS.PY — Prompt para el LLM de decisiones

### 🎯 Qué hace
Un prompt especializado que usa el LLM para **interpretar el contexto completo** y sugerir decisiones que las reglas simples no pueden capturar (matices, ironías, contexto cultural).

### 🔑 Código

```python
# src/decisions/prompts.py

RISK_ANALYSIS_PROMPT = """Eres un Community Manager senior experto en retención de comunidades tech.

Tu tarea es evaluar si un miembro de la comunidad está en riesgo de abandonar el programa de formación.

## Señales de abandono (churn):
- Frustración técnica repetida sin resolución
- Quejas sobre cursos, plataforma o mentores
- Aislamiento progresivo (deja de participar)
- Menciones de falta de tiempo o motivación
- Comparaciones negativas con otras plataformas

## Señales de fidelización (retención):
- Agradecimientos y reconocimientos
- Logros alcanzados (proyectos, empleos, certificaciones)
- Ayuda activa a otros miembros
- Participación constante en actividades

## Formato de respuesta (SOLO JSON):
{
  "nivel_riesgo": 0.0-1.0,
  "razon": "explicación breve del porqué",
  "accion_sugerida": "contactar_individualmente|monitorear|recompensar|invitar_a_mentoria",
  "momento_oportuno": "¿cuándo sería mejor intervenir?",
  "sentimiento_tendencia": "mejorando|estable|empeorando"
}

## Ejemplos:

Mensajes recientes del miembro:
"Ya no entiendo nada del curso de OCI, llevo 3 semanas trabado en el mismo proyecto"
"No me funciona el bucket, error tras error"
"Quizás esto no es para mí..."

Respuesta: {"nivel_riesgo": 0.85, "razon": "Frustración técnica prolongada + dudas sobre su capacidad + lenguaje de abandono", "accion_sugerida": "contactar_individualmente", "momento_oportuno": "dentro de 24 horas, antes de que se decida a abandonar", "sentimiento_tendencia": "empeorando"}
"""

RECURRING_DUDA_PROMPT = """Eres un analista de contenido educativo.

Detectas si dos o más preguntas de estudiantes se refieren AL MISMO TEMA aunque estén escritas con palabras diferentes.

## Ejemplos de equivalencia:
- "No puedo crear bucket en OCI" == "Error al crear objeto storage"
- "Cómo hago router en LangGraph" == "Nodos condicionales en LangGraph"
- "La interfaz de Streamlit no carga" == "st.set_page_config no funciona"

## Formato de respuesta (SOLO JSON):
{
  "es_recurrente": true|false,
  "tema_general": "nombre unificado del tema",
  "mensajes_relacionados": [ids de mensajes],
  "confianza": 0.0-1.0
}
"""
```

---

## 7️⃣ INTEGRACIÓN con el pipeline principal

### Modificación 1: `src/analysis/orchestrator.py`
Ahora el análisis retorna también el **texto original** y el **autor** (necesario para decisiones):

```python
def full_analysis(message: dict, llm_client) -> dict:
    # ... (código existente)
    return {
        "id": message.get("id"),
        "autor": message.get("autor"),
        "texto": message.get("texto"),
        "canal": message.get("canal"),
        "analisis": {
            "sentimiento": sentimiento,
            "temas": categorias.get("categorias", []),
            "relevancia_marketing": relevancia,
            "categoria_sugerida": _sugerir_categoria(...)
        }
    }
```

### Modificación 2: `src/orchestration/pipeline.py`
Ahora el pipeline llama al DecisionEngine DESPUÉS de generar activos:

```python
from src.decisions.engine import DecisionEngine

class CommunityPulsePipeline:
    def __init__(self, llm_client, oci_client, historial=None):
        self.llm = llm_client
        self.oci = oci_client
        self.router = ContentRouter()
        self.decisions = DecisionEngine(llm_client, historial)  # NUEVO
    
    async def process(self, input_data: dict) -> dict:
        # Paso 1-2: Normalizar + analizar (existente)
        messages = normalize_batch(...)
        analyses = await asyncio.gather(*[
            full_analysis(msg, self.llm) for msg in messages
        ])
        
        # Paso 2.5: DECISIONES  ← NUEVO
        batch_analysis = {
            "periodo_referencia": input_data.get("periodo_referencia"),
            "mensajes_analizados": analyses
        }
        decisiones = self.decisions.process_batch(batch_analysis)
        
        # Paso 3: Generar activos + notificaciones
        assets = {}
        notificaciones = []
        
        for decision in decisiones["acciones_recomendadas"]:
            if decision["tipo"] == "publicar_prioritario":
                # Generar post LinkedIn priorizando el mensaje
                activo = await generate_linkedin_post(decision, self.llm)
                assets[activo["tipo"]] = activo
                notificaciones.append(build_publication_priority(decision))
            
            elif decision["tipo"] in ["generar_faq", "derivar_mentoria"]:
                activo = await generate_faq_tip(decision, self.llm)
                assets.setdefault("faq_tips", []).append(activo)
                notificaciones.append(build_mentorship_referral(decision, escalamiento))
            
            # alertas no generan activos, solo notificaciones
        
        # Paso 4: Guardar TODO en OCI (incluyendo decisiones)
        package = self._build_package(input_data, analyses, assets, decisiones)
        oci_result = await save_assets_to_oci(self.oci, package)
        
        # Paso 5: Retornar respuesta con decisiones
        return self._build_response(analyses, assets, decisiones, oci_result)
```

### Modificación 3: Dashboard (Streamlit) — ver decisiones

```python
# src/interface/components/alerts_panel.py
import streamlit as st

def render_alerts(decisiones: dict):
    """Renderiza el panel de alertas y decisiones."""
    st.subheader("🚨 Decisiones Automáticas")
    
    resumen = decisiones.get("resumen_ejecutivo", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Miembros en riesgo", resumen.get("miembros_en_riesgo", 0))
    col2.metric("Dudas recurrentes", resumen.get("dudas_detectadas", 0))
    col3.metric("Testimonios destacables", resumen.get("testimonios_destacables", 0))
    
    st.markdown("---")
    
    for accion in decisiones.get("acciones_recomendadas", []):
        tipo = accion["tipo"]
        if tipo == "alerta_miembro":
            st.error(f"""⚠️ **ALERTA - {accion.get('autor', '')}**
            
{accion.get('razon', '')}
*Nivel de riesgo: {accion.get('nivel_riesgo', 0):.0%}*
*Acción sugerida: {accion.get('accion_sugerida', '')}*""")
        
        elif tipo == "derivar_mentoria":
            st.warning(f"""📚 **DERIVACIÓN A MENTORÍA**
            
Tema: {accion.get('tema', '')} 
Veces detectada: {accion.get('veces_detectada', 0)}
Mentor: {accion.get('mentor_sugerido', '')}""")
        
        elif tipo == "publicar_prioritario":
            st.success(f"""🚀 **PUBLICAR PRIORITARIO**
            
{accion.get('razon', '')}
Prioridad: {accion.get('prioridad', '')}""")
```

---

## 🧪 Cómo testear el módulo de decisiones

```python
# tests/test_decisions.py
import pytest
from src.decisions.engine import DecisionEngine
from src.decisions.member_risk import MemberRiskDetector
from src.decisions.recurring_topics import RecurringTopicsDetector
from src.decisions.escalation import EscalationRules

def test_testimonio_prioritario():
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "1",
            "autor": "Mariana",
            "categoria_sugerida": "caso_exito",
            "relevancia": 0.92,
            "sentimiento": {"score": 0.95}
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "publicar_prioritario" for a in acciones)

def test_duda_tecnica_genera_faq():
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "2",
            "autor": "Lucas",
            "categoria_sugerida": "faq_tip",
            "temas": ["langgraph"]
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "generar_faq" for a in acciones)

def test_sentimiento_negativo_alerta():
    engine = DecisionEngine(llm_client=Mock())
    batch = {
        "mensajes_analizados": [{
            "id": "3",
            "autor": "João",
            "sentimiento": {"etiqueta": "negativo", "score": 0.2}
        }]
    }
    resultado = engine.process_batch(batch)
    acciones = resultado["acciones_recomendadas"]
    assert any(a["tipo"] == "alerta_sentimiento_puntual" for a in acciones)

def test_member_risk_detection():
    detector = MemberRiskDetector(llm_client=Mock(), historial={
        "miembros_tracking": {
            "João": {"sentimiento_promedio": 0.7}
        }
    })
    mensajes = [
        {"texto": "No me funciona nada", "sentimiento": {"score": 0.2}},
        {"texto": "error tras error en OCI, me rindo", "sentimiento": {"score": 0.1}},
    ]
    resultado = detector.evaluate_author("João", mensajes)
    assert resultado["nivel_riesgo"] > 0.6
    assert "frustracion" in resultado["razon"]

def test_recurring_topics():
    detector = RecurringTopicsDetector(umbral=3)
    historial = [
        {"tema": "langgraph", "veces": 2},
        {"tema": "OCI", "veces": 1},
    ]
    mensajes = [
        {"temas": ["langgraph"], "categoria_sugerida": "faq_tip"},
        {"temas": ["langgraph"], "categoria_sugerida": "faq_tip"},
    ]
    resultado = detector.detect(mensajes, historial)
    assert any(d["tema"] == "langgraph" for d in resultado)
    assert resultado[0]["mentor_sugerido"] == "especialista_langgraph"

def test_escalation_classification():
    reglas = EscalationRules()
    
    critico = reglas.classify({"nivel_riesgo": 0.9})
    assert critico["nivel"] == "CRITICO"
    
    alto = reglas.classify({"nivel_riesgo": 0.7})
    assert alto["nivel"] == "ALTO"
    
    medio = reglas.classify({"nivel_riesgo": 0.5})
    assert medio["nivel"] == "MEDIO"
    
    info = reglas.classify({"nivel_riesgo": 0.1})
    assert info["nivel"] == "INFO"
```

---

## 📋 Resumen: qué se agrega al proyecto

| Componente | Archivo | Día de implementación | Responsable |
|------------|---------|----------------------|-------------|
| Motor de decisiones | `src/decisions/engine.py` | Día 6 | SE + DS1 |
| Detector de riesgo | `src/decisions/member_risk.py` | Día 6 | DS1 + DS2 |
| Detector de dudas recurrentes | `src/decisions/recurring_topics.py` | Día 6 | DS2 |
| Reglas de escalamiento | `src/decisions/escalation.py` | Día 7 | SE |
| Notificaciones | `src/decisions/notifications.py` | Día 7 | SE + BE |
| Prompts de decisión | `src/decisions/prompts.py` | Día 6 | DS3 |
| Integración pipeline | `src/orchestration/pipeline.py` (modificado) | Día 7 | SE |
| Panel de alertas | `src/interface/components/alerts_panel.py` | Día 7 | SE |
| Tests | `tests/test_decisions.py` | Día 7 | DS1 |

---

## 🎬 Lo que esto le da a la demo

**Escenario para el jurado:**

> *"Recibimos 20 mensajes de la comunidad esta semana. Nuestro sistema:*
> 
> 1. *Detectó que **Mariana** consiguió empleo → generó post LinkedIn automáticamente con prioridad ALTA* 🚀
> 2. *Detectó que **la duda de LangGraph** ya apareció 3 veces → generó FAQ + la derivó al mentor de Orquestación* 📚
> 3. *Detectó que **João** lleva 3 semanas con sentimiento negativo cayendo → ALERTA al community manager para intervenir HOY antes de que abandone* ⚠️
> 
> **No solo generamos contenido. Gestionamos la comunidad.**"*

Ese paralelo final es lo que hace ganar un hackathon.

---

*Módulo diferencial creado para equipo Community Pulse — Oracle ONE Hackathon G10*