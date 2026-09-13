from intelligence_core.embeddings.embedder import (
    embed
)

from intelligence_core.embeddings.similarity import (
    cosine_similarity
)

from intelligence_core.embeddings.vector_store import (
    load_vectors
)


def search(
    query,
    limit=5
):

    q = embed(query)

    scores = []

    for item in load_vectors():

        score = cosine_similarity(
            q,
            item["embedding"]
        )

        scores.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(score)
            }
        )

    scores.sort(
        key=lambda x:
        x["score"],
        reverse=True
    )

    return scores[:limit]
