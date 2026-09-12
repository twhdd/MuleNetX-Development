import hashlib
import hmac
import os


SECRET_KEY = os.getenv(
    "MULENETX_SECRET",
    "change_me"
)


def sign_payload(
    payload: str
):

    return hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_signature(
    payload: str,
    signature: str
):

    expected = sign_payload(
        payload
    )

    return hmac.compare_digest(
        expected,
        signature
    )
