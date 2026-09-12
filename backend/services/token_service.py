from datetime import datetime
from datetime import timedelta

from jose import jwt


SECRET = "mulenetx_refresh_secret"


def create_refresh_token(
    username
):

    return jwt.encode(
        {
            "sub": username,
            "exp":
            datetime.utcnow()
            +
            timedelta(days=30)
        },
        SECRET,
        algorithm="HS256"
    )


def verify_refresh_token(
    token
):

    return jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"]
    )
