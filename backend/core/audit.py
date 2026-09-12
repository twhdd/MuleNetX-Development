import json
from pathlib import Path
from datetime import datetime


AUDIT_LOG = Path(
    "logs/audit.log"
)

AUDIT_LOG.parent.mkdir(
    exist_ok=True
)


def log_event(
    action,
    actor,
    metadata=None
):

    event = {
        "timestamp":
        datetime.utcnow().isoformat(),

        "action":
        action,

        "actor":
        actor,

        "metadata":
        metadata or {}
    }

    with open(
        AUDIT_LOG,
        "a"
    ) as f:

        f.write(
            json.dumps(event)
        )

        f.write("\n")
