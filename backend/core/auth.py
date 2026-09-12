from datetime import datetime
from datetime import timedelta

from jose import jwt
from passlib.context import CryptContext


SECRET_KEY = "mulenetx-secret"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password):

    return pwd_context.hash(
        password
    )


def verify_password(
    plain,
    hashed
):

    return pwd_context.verify(
        plain,
        hashed
    )


def create_access_token(
    username,
    role
):

    payload = {
        "sub": username,
        "role": role,
        "exp":
        datetime.utcnow()
        +
        timedelta(
            minutes=
            ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(
    token
):

    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[
            ALGORITHM
        ]
    )
