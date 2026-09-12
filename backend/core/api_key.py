import os

from fastapi import (
    HTTPException,
    Header
)


API_KEY = os.getenv(
    "MULENETX_API_KEY",
    "mule-dev-key"
)


def require_api_key(
    x_api_key: str = Header(
        default=""
    )
):

    if x_api_key != API_KEY:

        raise HTTPException(
            status_code=401,
            detail="Invalid API Key"
        )
