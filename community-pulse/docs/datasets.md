# 📊 Fuentes de Datos — Procedencia y Licencias

> Documentar aquí la procedencia de CADA dataset usado.
> Obligatorio para demostrar cumplimiento legal en la demo.

## Datos Simulados (MVP rápido)

| Archivo | Origen | Licencia | Uso |
|---------|--------|----------|-----|
| `data/sample/messages.json` | Creado por el equipo según ejemplo del PDF | Libre | Demo de desarrollo |

## Datos Reales (para presentación final)

### Opción A: Hugging Face — Discord Dialogues
- **URL:** https://huggingface.co/datasets/mooaoeu/Discord-Dialogues
- **Contenido:** 7.3M intercambios de Discord anonimizados
- **Licencia:** Pública (adhiere a Discord ToS)
- **Uso:** Mensajes de comunidad para análisis

### Opción B: Kaggle — Reddit Comments Sentiment
- **URL:** https://www.kaggle.com/datasets/bornaetminan/reddit-comments-sentiment-dataset
- **Contenido:** Comentarios Reddit con labels de sentimiento
- **Licencia:** CC BY 4.0
- **Uso:** Validación del análisis de sentimiento (ground truth)

### Opción C: Kaggle — Coursera Course Reviews
- **URL:** https://www.kaggle.com/datasets/septa97/100k-courseras-course-reviews-dataset
- **Contenido:** 100K+ reviews de cursos
- **Licencia:** Uso académico
- **Uso:** Testimonios de estudiantes

### Opción D: Hugging Face — GitHub Issues
- **URL:** https://huggingface.co/datasets/helmo/github-issues
- **Contenido:** 7,540 issues/PRs con comentarios y reacciones
- **Licencia:** Apache 2.0
- **Uso:** Dudas técnicas → FAQs

## ⚠️ Prohibido / Evitar

| Fuente | Motivo |
|--------|--------|
| Scraping Discord API | Prohibido por Discord Developer Policy |
| Scraping Coursera | Bloqueado (Cloudflare) + ToS restrictiva |
| Scraping LinkedIn | Prohibido por ToS |

## ✅ Permisible con cuidado

| Fuente | Condición |
|--------|-----------|
| Reddit API (PRAW) | App oficial registrada + rate limits |
| Propia comunidad (Discord export) | Consentimiento de miembros + anonimización |

---

## Scripts de Descarga (`scripts/`)

### Estructura del flujo

```
scripts/download_datasets.py  →  data/real/*.json  (crudo)
scripts/prepare_samples.py    →  data/processed/dataset_combinado.json (listo para pipeline)
scripts/verify_dataset.py     →  stdout + exit code (0=ok)
```

### Uso rápido

```bash
# 1. Descargar todo (requiere: pip install datasets kagglehub pandas)
python scripts/download_datasets.py --all

# 2. O descargar solo fuentes específicas
python scripts/download_datasets.py --discord
python scripts/download_datasets.py --github
python scripts/download_datasets.py --reddit
python scripts/download_datasets.py --coursera

# 3. Preparar dataset combinado (filtra textos <10 chars, agrega id/origen)
python scripts/prepare_samples.py
python scripts/prepare_samples.py --mini   # Solo 50 por fuente (demo rápida)

# 4. Verificar que cumple el contrato del pipeline
python scripts/verify_dataset.py
python scripts/verify_dataset.py --quiet   # Solo exit code (para CI)
```

### Contrato de datos (MessageSchema Pydantic)

```json
{
    "id": "github_issues_123456",
    "autor": "usuario",
    "canal": "#open",
    "tipo": "general",
    "texto": "mínimo 10 caracteres...",
    "timestamp": "2025-06-13T00:00:00Z",
    "origen": "github_issues",
    "metadata": {}
}
```

### Esquemas de cada fuente (verificados)

| Fuente | HF/Kaggle API key | Size | Campos clave |
|--------|-------------------|------|--------------|
| Discord-Dialogues | No (HF público) | 7.3M rows | `text` (ChatML) |
| GitHub Issues | No (HF público) | 7.5K rows | `title`, `body`, `state`, `user`, `labels`, `reactions` |
| Reddit Sentiment | Sí (Kaggle acct) | ~100K rows | `body`, `label`, `subreddit` |
| Coursera Reviews | Sí (Kaggle acct) | ~100K rows | `Review`, `Label`, `CourseId` |
