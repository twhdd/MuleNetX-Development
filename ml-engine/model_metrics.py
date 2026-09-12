import os
import json
import pandas as pd
import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score
)

from ml_engine.inference.model_loader import load_model

BASE_DIR = os.path.dirname(__file__)
PREDICTIONS_PATH = os.path.join(BASE_DIR, "..", "datasets", "test_predictions.csv")
CONFIG_PATH = os.path.join(BASE_DIR, "models", "model_config.json")


def evaluate_test_set():
    if not os.path.exists(PREDICTIONS_PATH):
        raise FileNotFoundError("test_predictions.csv not found. Run train_model.py first.")

    pred_df = pd.read_csv(PREDICTIONS_PATH)
    y_true = pred_df["actual_label"].values
    y_pred = pred_df["predicted_label"].values
    y_prob = pred_df["fraud_probability"].values

    cm = confusion_matrix(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    support = int(y_true.sum())

    print("=== XGBoost Test Metrics ===")
    print("Confusion Matrix:")
    print(cm)
    print(f"Precision:     {prec:.4f}")
    print(f"Recall:        {rec:.4f}")
    print(f"F1 Score:      {f1:.4f}")
    print(f"ROC-AUC:       {roc_auc:.4f}")
    print(f"PR-AUC:        {pr_auc:.4f}")
    print(f"Fraud Support: {support}")

    # Majority class baseline
    base_pred = np.zeros_like(y_true)
    base_cm = confusion_matrix(y_true, base_pred)
    base_prec = precision_score(y_true, base_pred, zero_division=0)
    base_rec = recall_score(y_true, base_pred, zero_division=0)
    base_f1 = f1_score(y_true, base_pred, zero_division=0)
    base_roc = 0.5000
    base_pr = float(y_true.mean())

    print("\n=== Majority Baseline Metrics ===")
    print("Confusion Matrix:")
    print(base_cm)
    print(f"Precision:     {base_prec:.4f}")
    print(f"Recall:        {base_rec:.4f}")
    print(f"F1 Score:      {base_f1:.4f}")
    print(f"ROC-AUC:       {base_roc:.4f}")
    print(f"PR-AUC:        {base_pr:.4f}")


if __name__ == "__main__":
    evaluate_test_set()
