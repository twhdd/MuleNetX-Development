import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    precision_recall_curve
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.model_integrity import file_sha256
from graph_engine.point_in_time_features import build_point_in_time_dataset

DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "account_features.csv")
MODEL_DIR = os.path.join(PROJECT_ROOT, "ml_engine", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgb_fraud.pkl")
CONFIG_PATH = os.path.join(MODEL_DIR, "model_config.json")
MANIFEST_PATH = os.path.join(MODEL_DIR, "model_manifest.json")
PREDICTIONS_PATH = os.path.join(PROJECT_ROOT, "datasets", "test_predictions.csv")
ALT_PREDICTIONS_PATH = os.path.join(PROJECT_ROOT, "ml_engine", "predictions.csv")

NON_FEATURE_COLUMNS = [
    "account_id",
    "label",
    "target",
    "first_step",
    "cutoff_step",
    "split",
    "max_observed_step",
    "target_eligible",
    "target_censored",
    "fraud_transaction_count",
    "fraud_transaction_ratio"
]


def run_training_pipeline():
    print("=" * 60)
    print("PHASE 3: POINT-IN-TIME XGBOOST FRAUD DETECTION + EVALUATION")
    print("=" * 60)

    # 1. Ensure fresh point-in-time dataset is built
    print("\n--- 1. Point-in-Time Data Loading ---")
    df = pd.read_csv(DATASET_PATH)
    required_target_columns = {
        "target",
        "max_observed_step",
        "target_eligible",
        "target_censored",
    }
    if "split" not in df.columns or not required_target_columns.issubset(df.columns):
        print("Regenerating leak-free point-in-time features...")
        df = build_point_in_time_dataset(DATASET_PATH)

    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    print("Missing values per column:", dict(df.isnull().sum()))
    assert df.isnull().sum().sum() == 0, "Point-in-time dataset contains null values"
    if "target_eligible" in df.columns:
        df = df[df["target_eligible"]].copy()

    # 2. Labeling & Class Distribution
    print("\n--- 2. Label Verification ---")
    pos_count = int((df["target"] == 1).sum())
    neg_count = int((df["target"] == 0).sum())
    total_count = len(df)
    print(f"Total Accounts:    {total_count}")
    print(f"Fraud Accounts:    {pos_count} ({pos_count / total_count * 100:.2f}%)")
    print(f"Non-Fraud Accounts:{neg_count} ({neg_count / total_count * 100:.2f}%)")

    # 3. Temporal Split
    print("\n--- 3. Strict Temporal Train / Validation / Test Split ---")
    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    print(f"Features used ({len(feature_cols)}): {feature_cols}")

    X_train = train_df[feature_cols]
    y_train = train_df["target"]
    X_val = val_df[feature_cols]
    y_val = val_df["target"]
    X_test = test_df[feature_cols]
    y_test = test_df["target"]

    print(f"Train set (cutoff step 4): {len(X_train)} accounts (Fraud: {y_train.sum()}, Non-fraud: {len(y_train) - y_train.sum()})")
    print(f"Val set   (cutoff step 5): {len(X_val)} accounts (Fraud: {y_val.sum()}, Non-fraud: {len(y_val) - y_val.sum()})")
    print(f"Test set  (cutoff step 7): {len(X_test)} accounts (Fraud: {y_test.sum()}, Non-fraud: {len(y_test) - y_test.sum()})")

    # 4. Model Training
    print("\n--- 4. Model Training (XGBoost) ---")
    scale_pos_weight = float((len(y_train) - y_train.sum()) / max(y_train.sum(), 1))
    print(f"Class imbalance weighting (scale_pos_weight): {scale_pos_weight:.2f}")

    xgb_params = {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "scale_pos_weight": scale_pos_weight,
        "eval_metric": "logloss",
        "random_state": 42
    }

    model = XGBClassifier(**xgb_params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    # 5. Threshold Selection on Validation Set Only
    print("\n--- 5. Validation Threshold Selection ---")
    val_probs = model.predict_proba(X_val)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_val, val_probs)
    f1_scores = 2 * (precisions * recalls) / np.maximum(precisions + recalls, 1e-8)
    valid_idx = np.argmax(f1_scores[:-1]) if len(thresholds) > 0 else 0
    selected_threshold = float(thresholds[valid_idx]) if len(thresholds) > 0 else 0.5
    # Bound threshold sensibly between 0.1 and 0.8
    if selected_threshold > 0.8:
        selected_threshold = 0.5
    elif selected_threshold < 0.1:
        selected_threshold = 0.5

    print(f"Selected Decision Threshold from validation: {selected_threshold:.4f}")

    # 6. Evaluation on Untouched Test Set
    print("\n--- 6. Test Set Evaluation ---")
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= selected_threshold).astype(int)

    cm = confusion_matrix(y_test, test_preds)
    prec = precision_score(y_test, test_preds, zero_division=0)
    rec = recall_score(y_test, test_preds, zero_division=0)
    f1 = f1_score(y_test, test_preds, zero_division=0)
    roc_auc = roc_auc_score(y_test, test_probs)
    pr_auc = average_precision_score(y_test, test_probs)
    fraud_support = int(y_test.sum())

    print("Confusion Matrix:\n", cm)
    print(f"Precision:     {prec:.4f}")
    print(f"Recall:        {rec:.4f}")
    print(f"F1 Score:      {f1:.4f}")
    print(f"ROC-AUC:       {roc_auc:.4f}")
    print(f"PR-AUC:        {pr_auc:.4f}")
    print(f"Fraud Support: {fraud_support}")

    # 7. Baseline Comparison
    print("\n--- 7. Baseline Comparison (Majority Class Classifier) ---")
    base_preds = np.zeros_like(y_test)
    base_cm = confusion_matrix(y_test, base_preds)
    base_prec = precision_score(y_test, base_preds, zero_division=0)
    base_rec = recall_score(y_test, base_preds, zero_division=0)
    base_f1 = f1_score(y_test, base_preds, zero_division=0)
    base_roc = 0.5000
    base_pr = float(y_test.mean())

    print("Baseline Confusion Matrix:\n", base_cm)
    print(f"Baseline Precision: {base_prec:.4f}")
    print(f"Baseline Recall:    {base_rec:.4f}")
    print(f"Baseline F1 Score:  {base_f1:.4f}")
    print(f"Baseline ROC-AUC:   {base_roc:.4f}")
    print(f"Baseline PR-AUC:    {base_pr:.4f}")

    # 8. Save Model and Configuration
    print("\n--- 8. Saving Model Artifacts ---")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    sha256 = file_sha256(MODEL_PATH)
    manifest = {
        "model": "xgb_fraud.pkl",
        "sha256": sha256
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    config = {
        "features": feature_cols,
        "parameters": xgb_params,
        "decision_threshold": selected_threshold,
        "scale_pos_weight": scale_pos_weight,
        "metrics": {
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "fraud_support": fraud_support
        }
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # 9. Save Predictions
    predictions_df = pd.DataFrame({
        "account_id": test_df["account_id"].values,
        "fraud_probability": test_probs,
        "predicted_label": test_preds,
        "actual_label": y_test.values
    })
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    predictions_df.to_csv(ALT_PREDICTIONS_PATH, index=False)
    print(f"Predictions saved to {PREDICTIONS_PATH} ({len(predictions_df)} rows)")

    results = {
        "dataset_counts": {
            "total_accounts": total_count,
            "fraud_accounts": pos_count,
            "non_fraud_accounts": neg_count
        },
        "split_counts": {
            "train_accounts": len(X_train),
            "train_fraud": int(y_train.sum()),
            "val_accounts": len(X_val),
            "val_fraud": int(y_val.sum()),
            "test_accounts": len(X_test),
            "test_fraud": int(y_test.sum())
        },
        "model_config": config,
        "test_metrics": {
            "confusion_matrix": cm.tolist(),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(roc_auc),
            "pr_auc": float(pr_auc),
            "fraud_support": fraud_support
        },
        "baseline_metrics": {
            "confusion_matrix": base_cm.tolist(),
            "precision": float(base_prec),
            "recall": float(base_rec),
            "f1": float(base_f1),
            "roc_auc": float(base_roc),
            "pr_auc": float(base_pr)
        },
        "saved_paths": {
            "model_path": MODEL_PATH,
            "model_config_path": CONFIG_PATH,
            "model_manifest_path": MANIFEST_PATH,
            "predictions_path": PREDICTIONS_PATH
        }
    }

    return results


if __name__ == "__main__":
    run_training_pipeline()
