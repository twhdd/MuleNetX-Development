import json
import os
import joblib

from backend.core.model_integrity import (
    file_sha256
)


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml_engine", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgb_fraud.pkl")
MANIFEST = os.path.join(MODEL_DIR, "model_manifest.json")


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
