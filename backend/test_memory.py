from hindsight_memory import setup_bank, remember, recall


setup_bank()

remember(
    """
    Our codebase follows a strict Controller-Service-Repository
    architecture. Controllers must never access the database directly.
    Database operations belong in the Repository layer.
    """,
    context="Team architecture decision"
)

print("\nMemory stored successfully.")

results = recall(
    "What architecture rules does our team follow for database access?"
)

print("\nRecalled memories:")

for memory in results:
    print(f"\n[{memory.type}]")
    print(memory.text)