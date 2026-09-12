from fastapi import Request
from fastapi.responses import JSONResponse

from backend.core.rate_limit import (
    allow
)


async def rate_limit_middleware(
    request: Request,
    call_next
):

    ip = request.client.host

    if not allow(ip):

        return JSONResponse(
            status_code=429,
            content={
                "error":
                "Rate Limit Exceeded"
            }
        )

    return await call_next(
        request
    )
