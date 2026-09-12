from backend.core.metrics import (
    API_REQUESTS
)


async def metrics_middleware(
    request,
    call_next
):

    API_REQUESTS.inc()

    return await call_next(
        request
    )
