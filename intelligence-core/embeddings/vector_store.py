import json
from pathlib import Path


STORE = Path(
    "intelligence-core/embeddings/vectors.json"
)


def load_vectors():

    if not STORE.exists():

        with open(STORE, "w") as f:
            json.dump([], f)

    with open(STORE, "r") as f:
        return json.load(f)


def save_vectors(data):

    with open(STORE, "w") as f:
        json.dump(
            data,
            f
        )
