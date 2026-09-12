import json
from pathlib import Path


DB = Path(
    "investigation-engine/case_management/cases.json"
)


def load_cases():

    if not DB.exists():

        with open(DB, "w") as f:
            json.dump([], f)

    with open(DB, "r") as f:
        return json.load(f)


def save_cases(data):

    with open(DB, "w") as f:
        json.dump(
            data,
            f,
            indent=2
        )
