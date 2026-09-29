import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.hindsight_memory import recall, remember_lessons
from backend.groq_reviewer import review_code, extract_learning

app = FastAPI(title="Code Review Agent")

# Allow the static frontend (served from a different origin/port during
# local development, e.g. file:// or http://localhost:5500) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java",
    "C++", "C", "Go", "Rust", "SQL",
]

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "review_log.json"
_log_lock = threading.Lock()


class CodeRequest(BaseModel):
    code: str
    language: str = "Python"


def _load_log():
    try:
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _append_log(entry):
    with _log_lock:
        log = _load_log()
        log.append(entry)
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(json.dumps(log[-500:], indent=2), encoding="utf-8")


def _split_score(review_text):
    """Pull the 'SCORE: NN' first line out of the review."""
    match = re.match(r"\s*SCORE:\s*(\d{1,3})\s*\n?", review_text or "")
    if not match:
        return None, review_text
    return min(int(match.group(1)), 100), review_text[match.end():].lstrip()


@app.get("/")
def home():
    return {
        "message": "Code Review Agent is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/languages")
def languages():
    return {"languages": SUPPORTED_LANGUAGES}


@app.post("/review")
def review(request: CodeRequest):
    language = request.language if request.language in SUPPORTED_LANGUAGES else "Python"

    # 1. Recall relevant knowledge (biased toward this language)
    memories = recall(request.code, language=language)

    # 2. Review the code using remembered knowledge
    raw_review = review_code(request.code, memories, language=language)
    score, result = _split_score(raw_review)

    # 3. Extract reusable lessons from this review
    learning = extract_learning(request.code, result, language=language)

    # 4. Store each reusable lesson as its own memory
    stored = remember_lessons(learning, language=language)

    memory_texts = [memory.text for memory in memories]

    _append_log({
        "time": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "score": score,
        "memories_used": len(memory_texts),
        "lessons": stored,
    })

    return {
        "code": request.code,
        "language": language,
        "score": score,
        "memories_used": memory_texts,
        "review": result,
        "learning_stored": learning,
        "lessons": stored,
        "memory_updated": bool(stored),
    }


@app.get("/stats")
def stats():
    """Powers the Learning Dashboard: proof that the agent improves."""
    log = _load_log()

    by_language = {}
    for entry in log:
        by_language[entry["language"]] = by_language.get(entry["language"], 0) + 1

    scored = [e for e in log if e.get("score") is not None]
    recent_lessons = []
    for entry in reversed(log):
        for lesson in reversed(entry.get("lessons", [])):
            recent_lessons.append({"lesson": lesson, "language": entry["language"]})
        if len(recent_lessons) >= 8:
            break

    return {
        "total_reviews": len(log),
        "total_lessons": sum(len(e.get("lessons", [])) for e in log),
        "by_language": by_language,
        "score_history": [
            {"score": e["score"], "language": e["language"], "memories_used": e["memories_used"]}
            for e in scored[-15:]
        ],
        "recent_lessons": recent_lessons[:8],
    }


# Serves the frontend at http://localhost:8000/ui  keeps the JSON API
# routes above free to live at "/" and "/health".
app.mount(
    "/ui",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)
