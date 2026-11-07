"""
Community Pulse — Script maestro de descarga de datasets.

Uso:
    python scripts/download_datasets.py --all                # Descarga todo
    python scripts/download_datasets.py --discord           # Solo Discord
    python scripts/download_datasets.py --reddit            # Solo Reddit
    python scripts/download_datasets.py --github            # Solo GitHub Issues
    python scripts/download_datasets.py --coursera          # Solo Coursera

Requiere:
    pip install datasets kagglehub pandas

Nota sobre Kaggle:
    - kagglehub NO requiere cuenta (usa el nuevo sistema de descargas)
    - Si prefieren el CLI clásico: kaggle datasets download -d <dataset>
"""

import argparse
import json
import random
import shutil
from pathlib import Path

# Directorio destino
DATA_DIR = Path(__file__).parent.parent / "data" / "real"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

SAMPLE_SIZE = {
    "discord": 1000,     # 1000 mensajes de Discord
    "reddit": 2000,      # 2000 comentarios de Reddit
    "github": 500,       # 500 issues con comentarios
    "coursera": 500,     # 500 reviews de Coursera
}


def ensure_dirs():
    """Crea los directorios de datos."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# 1. DISCORD (HuggingFace) — mooaoeu/Discord-Dialogues
# ============================================
import re

_CHATML_TURNS = re.compile(r"<\|im_start\|>\s*(user|assistant)\s*(.*?)<\|im_end\|>", re.DOTALL)


def _parse_chatml(text: str):
    """Parsea texto ChatML y devuelve lista de (rol, mensaje)."""
    return [(m.group(1), m.group(2).strip()) for m in _CHATML_TURNS.finditer(text)]


def download_discord(sample: int = None):
    """Descarga y muestrea Discord Dialogues de HuggingFace.

    Esquema real del dataset (verificado en HF):
        text: str (ChatML multi-turno: <|im_start|>user|assistant ... <|im_end|>)
        tokens, turns, characters, words: int
    No tiene author/timestamp — los generamos.
    """
    sample = sample or SAMPLE_SIZE["discord"]
    print(f"📥 Descargando Discord Dialogues (sample: {sample})...")

    from datasets import load_dataset

    ds = load_dataset("mooaoeu/Discord-Dialogues", streaming=True)
    messages = []

    for i, row in enumerate(ds["train"]):
        if i >= sample * 3:  # recolectar 3x para luego muestrear
            break
        messages.append(row["text"])

    print(f"   Recolectadas {len(messages)} conversaciones, muestreando...")
    selected = random.sample(messages, min(sample // 2, len(messages)))

    # Convertir al formato estándar: cada turno ChatML = 1 interacción
    interacciones = []
    global _last_idx
    for chatml in selected:
        turns = _parse_chatml(chatml)
        for rol, texto in turns:
            if not texto:
                continue
            interacciones.append({
                "autor": f"discord_{rol}_{_last_idx:05d}",
                "canal": "#general",
                "tipo": "general",
                "texto": texto[:1000],
                "timestamp": "2025-01-01T00:00:00Z",
            })
            _last_idx += 1

    _save("discord_messages.json", interacciones)
    return len(interacciones)


# ============================================
# 2. REDDIT (Kaggle) — bornaetminan/reddit-comments-sentiment-dataset
# ============================================
def download_reddit(sample: int = None):
    """Descarga y muestrea Reddit Comments Sentiment de Kaggle."""
    sample = sample or SAMPLE_SIZE["reddit"]
    print(f"📥 Descargando Reddit Comments Sentiment (sample: {sample})...")

    try:
        import kagglehub
    except ImportError:
        raise SystemExit("❌ Instala kagglehub: pip install kagglehub")

    path = kagglehub.dataset_download("bornaetminan/reddit-comments-sentiment-dataset")
    print(f"   Dataset en: {path}")

    import pandas as pd

    # Encontrar el CSV principal
    files = list(Path(path).glob("*.csv"))
    if not files:
        raise FileNotFoundError("No se encontró CSV en el dataset descargado")
    df = pd.read_csv(files[0])

    # Columnas típicas: body, label, subreddit, created_at / o similares
    df = df.sample(min(sample, len(df)), random_state=42)

    interacciones = []
    for _, row in df.iterrows():
        text = str(row.get("body", row.get("clean_text", row.get("text", ""))))
        if not text or text == "nan":
            continue
        sent_label = row.get("label", "neutral")
        interacciones.append({
            "autor": row.get("username", row.get("author", "redditor")),
            "canal": f"r/{row.get('subreddit', 'general')}",
            "tipo": "general",
            "texto": text[:1000],
            "timestamp": str(row.get("created_at", "2025-01-01T00:00:00Z")),
            "metadata": {"sentiment_reference": str(sent_label)},
        })

    _save("reddit_comments.json", interacciones)
    return len(interacciones)


# ============================================
# 3. GITHUB ISSUES (HuggingFace) — helmo/github-issues
# ============================================
def download_github(sample: int = None):
    """Descarga y muestrea GitHub Issues de HuggingFace.

    Esquema real del dataset (verificado en HF):
        title: str, body: str (nullable), state: open|closed, user: {login},
        labels: [{name, ...}], reactions: {total_count, +1, -1, heart, ...},
        created_at: timestamp, number: int, comments: list
    """
    sample = sample or SAMPLE_SIZE["github"]
    print(f"📥 Descargando GitHub Issues (sample: {sample})...")

    from datasets import load_dataset

    ds = load_dataset("helmo/github-issues", split="train")
    selected = random.sample(range(len(ds)), min(sample, len(ds)))

    interacciones = []
    for idx in selected:
        row = ds[idx]
        title = row.get("title", "") or ""
        body_raw = row.get("body")
        body = body_raw.strip() if isinstance(body_raw, str) else ""

        texto = f"{title}\n{body}"[:1000] if body else title
        if not texto:
            continue

        user_data = row.get("user")
        autor = user_data.get("login", f"contributor_{idx}") if isinstance(user_data, dict) else "contributor"
        labels_raw = row.get("labels", []) or []
        labels = [l.get("name", "") for l in labels_raw if isinstance(l, dict)]

        # Solo contar reacciones numéricas, excluir "url" (str) y "total_count" (ya sumamos aparte)
        reactions_raw = row.get("reactions") or {}
        numeric_keys = {"+1", "-1", "confused", "eyes", "heart", "hooray", "laugh", "rocket"}
        reacciones = sum(v for k, v in reactions_raw.items() if k in numeric_keys and isinstance(v, int))

        created = row.get("created_at")
        timestamp = str(created) if created is not None else "2025-01-01T00:00:00Z"

        interacciones.append({
            "autor": autor,
            "canal": f"#{row.get('state', 'open')}",
            "tipo": "pregunta_tecnica" if row.get("state") == "open" else "general",
            "texto": texto,
            "timestamp": timestamp,
            "metadata": {
                "issue_number": row.get("number"),
                "labels": labels,
                "reacciones": reacciones,
            },
        })

    _save("github_issues.json", interacciones)
    return len(interacciones)


# ============================================
# 4. COURSERA REVIEWS (Kaggle) — septa97/100k-courseras-course-reviews-dataset
# ============================================
def download_coursera(sample: int = None):
    """Descarga y muestrea Coursera Course Reviews de Kaggle."""
    sample = sample or SAMPLE_SIZE["coursera"]
    print(f"📥 Descargando Coursera Course Reviews (sample: {sample})...")

    try:
        import kagglehub
    except ImportError:
        raise SystemExit("❌ Instala kagglehub: pip install kagglehub")

    path = kagglehub.dataset_download("septa97/100k-courseras-course-reviews-dataset")
    print(f"   Dataset en: {path}")

    import pandas as pd

    files = list(Path(path).glob("*.tsv")) + list(Path(path).glob("*.csv"))
    if not files:
        raise FileNotFoundError("No se encontró TSV/CSV en el dataset descargado")

    df = pd.read_csv(files[0], sep="\t" if files[0].suffix == ".tsv" else ",")
    df = df.sample(min(sample, len(df)), random_state=42)

    interacciones = []
    for _, row in df.iterrows():
        review = str(row.get("Review", row.get("review", "")))
        if not review or review == "nan":
            continue
        rating = row.get("Label", row.get("label", 5))
        sent = "muy_positivo" if int(rating) >= 5 else "positivo" if int(rating) >= 4 else "neutral" if int(rating) == 3 else "negativo"

        interacciones.append({
            "autor": f"estudiante_coursera_{_last_idx}",
            "canal": "#feedback-cursos",
            "tipo": "feedback",
            "texto": review[:1000],
            "timestamp": "2025-01-01T00:00:00Z",
            "metadata": {
                "rating": int(rating),
                "sentiment_reference": sent,
                "course_id": str(row.get("CourseId", row.get("course_id", ""))),
            },
        })

    _save("coursera_reviews.json", interacciones)
    return len(interacciones)


# Helpers
_last_idx = 0


def _save(filename: str, interacciones: list):
    """Guarda las interacciones en formato estándar del pipeline."""
    if not interacciones:
        print(f"❌ No se obtuvieron datos para {filename}")
        return

    global _last_idx
    _last_idx += len(interacciones)

    # Guardar solo una muestra SI es muy grande (> muéstralo completo si < 5000)
    paquete = {
        "origen_comunidad": filename.replace("_", " ").replace(".json", ""),
        "periodo_referencia": "Batch_01",
        "interacciones": interacciones,
    }

    destino = DATA_DIR / filename
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(paquete, f, ensure_ascii=False, indent=2)

    print(f"✅ Guardado: {destino} ({len(interacciones)} interacciones)")
    print(f"   Ejemplo: {interacciones[0]['texto'][:80]}...")


# ============================================
# MAIN
# ============================================
def main():
    parser = argparse.ArgumentParser(description="Descarga datasets reales para Community Pulse")
    parser.add_argument("--all", action="store_true", help="Descarga todos los datasets")
    parser.add_argument("--discord", action="store_true", help="Solo Discord Dialogues (HF)")
    parser.add_argument("--reddit", action="store_true", help="Solo Reddit Sentiment (Kaggle)")
    parser.add_argument("--github", action="store_true", help="Solo GitHub Issues (HF)")
    parser.add_argument("--coursera", action="store_true", help="Solo Coursera Reviews (Kaggle)")
    parser.add_argument("--size", type=int, default=None, help="Tamaño de muestra (default por dataset)")
    args = parser.parse_args()

    ensure_dirs()

    todos = args.all or not (args.discord or args.reddit or args.github or args.coursera)

    if todos or args.discord:
        try:
            n = download_discord(args.size)
            print(f"📊 Discord: {n} mensajes\n")
        except ImportError as e:
            print(f"⚠️ {e}. Instala: pip install datasets\n")

    if todos or args.reddit:
        try:
            n = download_reddit(args.size)
            print(f"📊 Reddit: {n} comentarios\n")
        except Exception as e:
            print(f"⚠️ Error Reddit: {e}. Instala: pip install kagglehub pandas\n")

    if todos or args.github:
        try:
            n = download_github(args.size)
            print(f"📊 GitHub: {n} issues\n")
        except ImportError as e:
            print(f"⚠️ {e}. Instala: pip install datasets\n")

    if todos or args.coursera:
        try:
            n = download_coursera(args.size)
            print(f"📊 Coursera: {n} reviews\n")
        except Exception as e:
            print(f"⚠️ Error Coursera: {e}. Instala: pip install kagglehub pandas\n")

    print("\n✅ Proceso completado. Archivos en data/real/")
    print("   Convertir todo al formato listo: python scripts/prepare_samples.py")


if __name__ == "__main__":
    main()