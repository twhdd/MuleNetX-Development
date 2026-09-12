import json

from backend.core.redis_client import (
    redis_client
)


def cache_get(key):

    value = redis_client.get(key)

    if value:
        return json.loads(value)

    return None


def cache_set(
    key,
    value,
    ttl=300
):

    redis_client.setex(
        key,
        ttl,
        json.dumps(value)
    )
