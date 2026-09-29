# Code Review Agent

A code review agent that remembers. Every review is checked against a
persistent bank of team engineering rules — architecture decisions, past
mistakes, security requirements — recalled through
[Hindsight](https://github.com/vectorize-io/hindsight). After each review,
the agent extracts any new reusable lessons and writes them back to the
same memory bank, so the next review (on a different file, days later) can
recall them too.

## How it works

```
 code  ──▶  recall(code)  ──▶  review_code(code, memories)  ──▶  review
                 │                                                  │
                 ▼                                                  ▼
         Hindsight memory bank                          extract_learning(code, review)
        (past team rules & lessons)  ◀────────── remember(learning) ──┘
```

1. **Recall** — `backend/hindsight_memory.py` queries the Hindsight bank
   for team rules relevant to the submitted code.
2. **Review** — `backend/groq_reviewer.py` sends the code plus the
   recalled memories to Groq (`openai/gpt-oss-120b`) and asks for a
   structured review that explicitly flags when a finding comes from team
   memory rather than a generic best practice.
3. **Extract** — a second Groq call pulls out only the *reusable* rules
   from that review (no code, no one-off bug descriptions, no dates or
   names) — see the prompt in `groq_reviewer.py` for the exact criteria.
4. **Retain** — those rules are written back to the Hindsight bank via
   `remember()`, so future reviews (of any file) can recall them.

This loop is what makes memory the point of the project rather than a
side feature: the agent's review quality is meant to visibly improve as
the bank accumulates team-specific rules, instead of staying generic
across every review.

## New in this version

- **Multi-language review** (Python, JavaScript, TypeScript, Java, C++, C, Go, Rust, SQL). A dropdown in the editor, per-language sample code, and an **Auto-detect** toggle that switches the language as you paste. The selected language is sent to `POST /review` and used in the review prompt, the memory recall query, and lesson extraction.
- **Memory-highlighted findings.** Any finding that comes from Hindsight memory is tagged `[MEMORY]` by the reviewer and shown in purple in the UI.
- **Quality score ring** (0-100) with the change since your previous review in that language.
- **Suggested Fix** section with a copy button on every code block.
- **"Learned from this review"** panel showing the exact rules written back to memory.
- **Agent Learning Dashboard** (`GET /stats`): reviews done, lessons remembered, languages covered, score trend, and the latest lessons. History is kept in `data/review_log.json`.
- `GET /languages` lists supported languages. Unknown languages fall back to Python.

## Project structure

```
code_review/
├── backend/
│   ├── main.py              FastAPI app — POST /review orchestrates recall → review → extract → remember
│   ├── groq_reviewer.py     Groq calls: review_code(), extract_learning()
│   ├── hindsight_memory.py  Hindsight client wrapper: remember(), recall(), setup_bank(), reset_bank()
│   └── test_memory.py       Standalone script to sanity-check the Hindsight bank
├── frontend/
│   └── index.html           Single-page UI: paste code, see memory recalled → review → lessons learned
├── memory/
│   └── memory.py            Legacy local-JSON memory prototype — superseded by hindsight_memory.py, kept for reference
├── data/
│   └── review_memory.json   Sample data used by the legacy local prototype
├── requirements.txt
└── .env                     API keys and config (not committed)
```

`memory/memory.py` predates the Hindsight integration — `main.py` only
imports from `backend/hindsight_memory.py`. It's left in the repo as a
reference for how the local prototype worked, but it isn't part of the
running app. Delete it if you'd rather keep the repo lean.

## Setup

**Requirements:** Python 3.10+, a [Groq API key](https://console.groq.com),
and a Hindsight instance (Hindsight Cloud or self-hosted).

```bash
cd code_review
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in the `code_review/` directory:

```
GROQ_API_KEY=your_groq_key
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your_hindsight_key
HINDSIGHT_BANK_ID=code-review-agent
```

Create the memory bank once:

```bash
python -c "from backend.hindsight_memory import setup_bank; setup_bank()"
```

## Running it

```bash
uvicorn backend.main:app --reload
```

- API: `http://localhost:8000` — `GET /health`, `POST /review`
- Frontend: `http://localhost:8000/ui` (served as static files by the
  same FastAPI app, so no separate server or CORS setup is needed)

### `POST /review`

Request:
```json
{ "code": "def process_order(order):\n    db.execute(f\"INSERT INTO orders VALUES ({order.id})\")" }
```

Response:
```json
{
  "code": "...",
  "memories_used": ["Database operations should not be written directly inside controllers."],
  "review": "structured review text...",
  "learning_stored": "one reusable rule per line...",
  "memory_updated": true
}
```

## Notes

- `hindsight_memory.py` exposes `reset_bank()` for wiping the bank during
  development — don't call it against a bank you care about.
- The frontend renders `memories_used` and `learning_stored` as separate
  chip rails specifically to make the recall → review → retain loop
  visible, since that's the part of the project Hindsight actually
  powers.
