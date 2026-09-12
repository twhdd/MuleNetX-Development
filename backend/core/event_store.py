from collections import deque


EVENTS = deque(
    maxlen=500
)


def push_event(
    event
):
    EVENTS.appendleft(
        event
    )


def get_events():
    return list(EVENTS)
