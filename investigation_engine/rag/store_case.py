from investigation_engine.rag.vector_store import (
    load_memory,
    save_memory
)


def store_case(
    account_id,
    report
):

    memory = load_memory()

    memory.append(
        {
            "account_id": account_id,
            "report": report
        }
    )

    save_memory(memory)
