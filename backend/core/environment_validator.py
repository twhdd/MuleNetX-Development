import os
from dotenv import load_dotenv


REQUIRED = [
    "MULENETX_API_KEY",
    "MULENETX_SECRET"
]


def validate_environment():
    load_dotenv()

    missing = []

    for item in REQUIRED:

        if not os.getenv(item):

            missing.append(
                item
            )

    if missing:

        raise RuntimeError(
            f"Missing: {missing}"
        )
