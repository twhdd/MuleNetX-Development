import json
import joblib

from backend.core.model_integrity import (
    file_sha256
)


MODEL_PATH = (
    "ml-engine/models/"
    "xgb_fraud.pkl"
)

MANIFEST = (
    "ml-engine/models/"
    "model_manifest.json"
)


def load_model():

    with open(
        MANIFEST
    ) as f:

        manifest = json.load(f)

    current = file_sha256(
        MODEL_PATH
    )

    if current != manifest["sha256"]:

        raise Exception(
            "Model Tampering Detected"
        )

    return joblib.load(
        MODEL_PATH
    )
