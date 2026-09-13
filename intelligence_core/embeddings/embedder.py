import os

import requests


OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/api/embeddings"
MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")


def embed(text: str):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": text
        },
        timeout=300
    )

    response.raise_for_status()

    return response.json()["embedding"]
