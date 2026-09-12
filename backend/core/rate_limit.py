from time import time


REQUESTS = {}

WINDOW = 60
MAX_REQUESTS = 100


def allow(ip):

    now = time()

    if ip not in REQUESTS:
        REQUESTS[ip] = []

    REQUESTS[ip] = [
        t
        for t in REQUESTS[ip]
        if now - t < WINDOW
    ]

    if len(
        REQUESTS[ip]
    ) >= MAX_REQUESTS:

        return False

    REQUESTS[ip].append(
        now
    )

    return True
