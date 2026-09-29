import os

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_API_URL = os.getenv(
    "HINDSIGHT_API_URL",
    "https://api.hindsight.vectorize.io"
)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")

BANK_ID = os.getenv(
    "HINDSIGHT_BANK_ID",
    "code-review-agent"
)

client = Hindsight(
    base_url=HINDSIGHT_API_URL,
    api_key=HINDSIGHT_API_KEY
)


def setup_bank():
    try:
        client.create_bank(
            bank_id=BANK_ID,
            name="Code Review Agent Memory"
        )
        print("Memory bank created.")
    except Exception as e:
        print(f"Bank already exists or could not be created: {e}")


def remember(content, context=None):
    if not content or not content.strip():
        return

    client.retain(
        bank_id=BANK_ID,
        content=content.strip(),
        context=context
    )


def remember_lessons(lessons, language=None):
    """Store each rule as its own memory so recall stays precise.

    Language-specific rules are tagged in the context, so a Java rule is
    found when reviewing Java and not when reviewing Go.
    """
    stored = []
    context = "Reusable engineering lesson extracted from a code review."
    if language:
        context = f"Reusable {language} engineering lesson extracted from a code review."

    for lesson in lessons.splitlines():
        lesson = lesson.strip()

        if not lesson:
            continue

        remember(content=lesson, context=context)
        stored.append(lesson)

    return stored


def recall(query, limit=5, language=None):
    """Recall memories relevant to the code. The language is put in the
    query so language-specific rules rank higher."""
    if language:
        query = f"{language} code review rules and past mistakes.\n\n{query}"

    result = client.recall(
        bank_id=BANK_ID,
        query=query
    )

    results = result.results or []

    return results[:limit]


def clear_bank():
    """
    Delete the current memory bank.

    WARNING:
    This permanently removes the existing memories in this bank.
    Use this only during development/testing.
    """
    try:
        client.delete_bank(bank_id=BANK_ID)
        print("Memory bank deleted.")
    except Exception as e:
        print(f"Could not delete memory bank: {e}")


def reset_bank():
    """
    Delete and recreate the memory bank.
    """
    clear_bank()
    setup_bank()
