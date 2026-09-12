import json
from pathlib import Path


DB_PATH = Path(
    "investigation-engine/rag/case_memory.json"
)


def load_memory():

    if not DB_PATH.exists():
        return []

    with open(DB_PATH, "r") as f:
        return json.load(f)


def save_memory(data):

    with open(DB_PATH, "w") as f:
        json.dump(
            data,
            f,
            indent=2
        )
