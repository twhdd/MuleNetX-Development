from intelligence_core.embeddings.embedder import (
    embed
)

from intelligence_core.embeddings.vector_store import (
    load_vectors,
    save_vectors
)


def index_case(
    case_id,
    content
):

    vectors = load_vectors()

    vectors.append(
        {
            "id": case_id,
            "content": content,
            "embedding": embed(content)
        }
    )

    save_vectors(vectors)
