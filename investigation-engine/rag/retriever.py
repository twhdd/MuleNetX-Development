from investigation_engine.rag.vector_store import (
    load_memory
)


def retrieve(account_id):

    memory = load_memory()

    matches = []

    for item in memory:

        if item["account_id"] == account_id:
            matches.append(item)

    return matches
