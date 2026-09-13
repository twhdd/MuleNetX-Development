import os
import sys
import json
import shap
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml_engine.inference.model_loader import load_model
from backend.neo4j_client import neo4j_client

MODELS_DIR = os.path.join(PROJECT_ROOT, "ml_engine", "models")
CONFIG_PATH = os.path.join(MODELS_DIR, "model_config.json")
FEATURES_PATH = os.path.join(PROJECT_ROOT, "datasets", "account_features.csv")

SHAP_VALUES_PATH = os.path.join(PROJECT_ROOT, "datasets", "shap_values.csv")
EXPLANATIONS_CSV_PATH = os.path.join(PROJECT_ROOT, "datasets", "account_explanations.csv")
EXPLANATIONS_JSON_PATH = os.path.join(PROJECT_ROOT, "ml_engine", "account_explanations.json")
GLOBAL_IMPORTANCE_CSV_PATH = os.path.join(PROJECT_ROOT, "datasets", "global_shap_importance.csv")
GLOBAL_IMPORTANCE_JSON_PATH = os.path.join(MODELS_DIR, "global_shap_importance.json")


def get_risk_category(risk_score: float) -> str:
    """Deterministic fixed-threshold risk category mapping."""
    if risk_score >= 80.0:
        return "CRITICAL"
    elif risk_score >= 50.0:
        return "HIGH"
    elif risk_score >= 20.0:
        return "MEDIUM"
    else:
        return "LOW"


def generate_account_explanation(
    account_id: str,
    fraud_prob: float,
    predicted_label: int,
    risk_score: float,
    risk_category: str,
    top_pos: List[Dict[str, Any]],
    top_neg: List[Dict[str, Any]]
) -> str:
    """Generates a deterministic factual explanation based strictly on feature and SHAP values."""
    action = "flagged for fraud review" if predicted_label == 1 else "cleared as standard behavior"
    pos_desc = ", ".join([f"{item['feature']} ({item['feature_value']:.2f}, SHAP +{item['shap_value']:.3f})" for item in top_pos[:3]])
    neg_desc = ", ".join([f"{item['feature']} ({item['feature_value']:.2f}, SHAP {item['shap_value']:.3f})" for item in top_neg[:2]])

    narrative = f"Account {account_id} is classified as {risk_category} Risk with a deterministic risk score of {risk_score:.1f}/100 (fraud probability: {fraud_prob:.4f}) and {action}."
    if top_pos:
        narrative += f" Key risk drivers pushing score higher include: {pos_desc}."
    if top_neg:
        narrative += f" Mitigating factors pushing score lower include: {neg_desc}."
    return narrative


def run_shap_analysis():
    print("=" * 60)
    print("PHASE 4: SHAP EXPLAINABILITY + RISK SCORING")
    print("=" * 60)

    # 1. Load exact frozen model and configuration
    print("\n--- 1. Loading Frozen Phase 3 Model ---")
    model = load_model()
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    feature_names = config["features"]
    decision_threshold = float(config.get("decision_threshold", 0.5))
    print(f"Loaded frozen model with {len(feature_names)} features.")
    print(f"Frozen decision threshold: {decision_threshold:.4f}")

    # 2. Load held-out test accounts
    print("\n--- 2. Loading Held-Out Test Accounts ---")
    df = pd.read_csv(FEATURES_PATH)
    test_df = df[df["split"] == "test"].copy().reset_index(drop=True)
    num_test = len(test_df)
    print(f"Number of test accounts to explain: {num_test}")

    X_test = test_df[feature_names]

    # Verify frozen predictions
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= decision_threshold).astype(int)

    # 3. Compute SHAP values
    print("\n--- 3. Computing Exact SHAP Values with TreeExplainer ---")
    explainer = shap.TreeExplainer(model)
    shap_matrix = explainer.shap_values(X_test)
    base_value = float(explainer.expected_value) if np.isscalar(explainer.expected_value) else float(explainer.expected_value[1] if len(explainer.expected_value) > 1 else explainer.expected_value[0])
    print(f"Computed SHAP values for {num_test} accounts across {len(feature_names)} features.")
    print(f"Expected base value: {base_value:.4f}")

    # 4. Global Feature Importance
    print("\n--- 4. Computing Global Feature Importance ---")
    mean_abs_shap = np.mean(np.abs(shap_matrix), axis=0)
    global_df = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": mean_abs_shap
    }).sort_values(by="mean_abs_shap", ascending=False).reset_index(drop=True)
    global_df["rank"] = range(1, len(global_df) + 1)
    print("Top 5 Global SHAP Features:")
    for idx, row in global_df.head(5).iterrows():
        print(f"  {int(row['rank'])}. {row['feature']:<28} Mean |SHAP| = {row['mean_abs_shap']:.4f}")

    # 5. Account-Level Explanations and Risk Scores
    print("\n--- 5. Generating Account-Level Risk Scores and Explanations ---")
    explanations_list = []
    shap_rows = []

    for i in range(num_test):
        acct_id = test_df.loc[i, "account_id"]
        prob = float(test_probs[i])
        pred = int(test_preds[i])
        actual = int(test_df.loc[i, "target"])
        risk_score = round(prob * 100.0, 2)
        risk_cat = get_risk_category(risk_score)

        acct_shap = shap_matrix[i]
        shap_dict = {"account_id": acct_id}
        for f_idx, f_name in enumerate(feature_names):
            shap_dict[f"shap_{f_name}"] = float(acct_shap[f_idx])
        shap_rows.append(shap_dict)

        # Attribution sorting
        contribs = []
        for f_idx, f_name in enumerate(feature_names):
            contribs.append({
                "feature": f_name,
                "feature_value": float(X_test.iloc[i, f_idx]),
                "shap_value": float(acct_shap[f_idx])
            })

        pos_contribs = sorted([c for c in contribs if c["shap_value"] > 0], key=lambda x: x["shap_value"], reverse=True)
        neg_contribs = sorted([c for c in contribs if c["shap_value"] < 0], key=lambda x: x["shap_value"])

        text_explanation = generate_account_explanation(
            account_id=acct_id,
            fraud_prob=prob,
            predicted_label=pred,
            risk_score=risk_score,
            risk_category=risk_cat,
            top_pos=pos_contribs,
            top_neg=neg_contribs
        )

        explanations_list.append({
            "account_id": acct_id,
            "fraud_probability": prob,
            "risk_score": risk_score,
            "risk_category": risk_cat,
            "predicted_label": pred,
            "actual_label": actual,
            "top_positive_contributors": pos_contribs[:5],
            "top_negative_contributors": neg_contribs[:5],
            "explanation": text_explanation
        })

    # Save output artifacts
    print("\n--- 6. Saving Reproducible Outputs ---")
    # 1. Global Importance
    global_df.to_csv(GLOBAL_IMPORTANCE_CSV_PATH, index=False)
    with open(GLOBAL_IMPORTANCE_JSON_PATH, "w") as f:
        json.dump(global_df.to_dict("records"), f, indent=2)

    # 2. Raw SHAP values
    shap_df = pd.DataFrame(shap_rows)
    shap_df.to_csv(SHAP_VALUES_PATH, index=False)

    # 3. Explanations JSON & CSV
    with open(EXPLANATIONS_JSON_PATH, "w") as f:
        json.dump(explanations_list, f, indent=2)

    exp_summary_df = pd.DataFrame([
        {
            "account_id": item["account_id"],
            "fraud_probability": item["fraud_probability"],
            "risk_score": item["risk_score"],
            "risk_category": item["risk_category"],
            "predicted_label": item["predicted_label"],
            "actual_label": item["actual_label"],
            "top_risk_driver": item["top_positive_contributors"][0]["feature"] if item["top_positive_contributors"] else "none",
            "top_risk_shap": item["top_positive_contributors"][0]["shap_value"] if item["top_positive_contributors"] else 0.0,
            "explanation": item["explanation"]
        }
        for item in explanations_list
    ])
    exp_summary_df.to_csv(EXPLANATIONS_CSV_PATH, index=False)

    print(f"Saved global importance to: {GLOBAL_IMPORTANCE_CSV_PATH}")
    print(f"Saved raw SHAP values to:   {SHAP_VALUES_PATH} ({len(shap_df)} rows)")
    print(f"Saved explanations to:      {EXPLANATIONS_CSV_PATH}")

    # 7. Write risk scores, categories, and top risk drivers to Neo4j
    print("\n--- 7. Updating Neo4j Account Nodes with Real Risk & Explanation Data ---")
    neo4j_records = []
    for item in explanations_list:
        top_drivers = ", ".join([c["feature"] for c in item["top_positive_contributors"][:3]])
        neo4j_records.append({
            "account_id": item["account_id"],
            "fraud_probability": item["fraud_probability"],
            "risk_score": item["risk_score"],
            "risk_category": item["risk_category"],
            "predicted_label": item["predicted_label"],
            "top_risk_drivers": top_drivers,
            "explanation": item["explanation"]
        })

    batch_size = 2500
    neo4j_update_query = """
    UNWIND $rows AS row
    MATCH (a:Account {account_id: row.account_id})
    SET a.fraud_probability = row.fraud_probability,
        a.risk_score = row.risk_score,
        a.risk_category = row.risk_category,
        a.predicted_label = row.predicted_label,
        a.top_risk_drivers = row.top_risk_drivers,
        a.explanation = row.explanation
    """
    for start in range(0, len(neo4j_records), batch_size):
        batch = neo4j_records[start:start + batch_size]
        neo4j_client.execute(neo4j_update_query, {"rows": batch})

    print(f"Successfully updated {len(neo4j_records)} Neo4j Account nodes with point-in-time risk scores and explanations.")

    # Display Example Explanation
    print("\n--- Example Account Explanation ---")
    crit_examples = [e for e in explanations_list if e["risk_category"] == "CRITICAL"]
    sample_ex = crit_examples[0] if crit_examples else explanations_list[0]
    print(f"Account:        {sample_ex['account_id']}")
    print(f"Risk Score:     {sample_ex['risk_score']} ({sample_ex['risk_category']})")
    print(f"Fraud Prob:     {sample_ex['fraud_probability']:.4f}")
    print(f"Predicted/True: {sample_ex['predicted_label']} / {sample_ex['actual_label']}")
    print(f"Top Positive:   {sample_ex['top_positive_contributors'][:3]}")
    print(f"Top Negative:   {sample_ex['top_negative_contributors'][:2]}")
    print(f"Explanation:    {sample_ex['explanation']}")

    return {
        "num_explained": num_test,
        "global_importance": global_df.head(5).to_dict("records"),
        "example": sample_ex
    }


if __name__ == "__main__":
    run_shap_analysis()
