import os
import json
import joblib
import pandas as pd
from typing import Optional

from ml_engine.inference.model_loader import load_model

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "model_config.json"
)


def predict(df: pd.DataFrame, model=None) -> pd.DataFrame:
    """Predicts fraud risk scores for given account feature DataFrame."""
    if model is None:
        model = load_model()

    feature_cols = None
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
            feature_cols = config.get("features")

    if feature_cols is None:
        exclude = ["account_id", "label", "first_step", "fraud_transaction_count", "fraud_transaction_ratio"]
        feature_cols = [c for c in df.columns if c not in exclude]

    X = df[feature_cols]
    probabilities = model.predict_proba(X)[:, 1]

    scored = df.copy()
    scored["risk_score"] = probabilities
    return scored


if __name__ == "__main__":
    features_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "datasets",
        "account_features.csv"
    )
    df = pd.read_csv(features_path)
    scored = predict(df)
    print("Scored Accounts Preview:")
    print(scored[["account_id", "risk_score"]].head())
