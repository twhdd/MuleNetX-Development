from fastapi import APIRouter

from intelligence_core.embeddings.search import (
    search
)

router = APIRouter()


@router.get(
    "/search"
)
def semantic_search(
    q: str
):

    return search(q)
