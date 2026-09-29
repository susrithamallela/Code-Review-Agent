import json
from pathlib import Path

MEMORY_FILE = Path("data/review_memory.json")


def load_memories():
    if not MEMORY_FILE.exists():
        return []

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(memory):
    memories = load_memories()
    memories.append(memory)

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memories, file, indent=4)


def search_memories(keyword):
    memories = load_memories()

    keyword = keyword.lower()

    results = []

    for memory in memories:
        text = json.dumps(memory).lower()

        if keyword in text:
            results.append(memory)

    return results
if __name__ == "__main__":
    results = search_memories("database")

    print("Relevant memories:")

    for memory in results:
        print(memory)