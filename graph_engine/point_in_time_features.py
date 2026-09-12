import os
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

from backend.neo4j_client import neo4j_client
from backend.database.session import engine

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "datasets",
    "account_features_pit.csv"
)
CANONICAL_FEATURES_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "datasets",
    "account_features.csv"
)


def get_account_temporal_metadata() -> pd.DataFrame:
    """Queries PostgreSQL for each account's first appearance step and ground-truth fraud label."""
    query = """
    WITH acct_steps AS (
        SELECT name_orig AS acct, step, is_fraud FROM transactions
        UNION ALL
        SELECT name_dest AS acct, step, is_fraud FROM transactions
    )
    SELECT 
        acct AS account_id, 
        min(step) AS first_step,
        max(is_fraud) AS label
    FROM acct_steps
    GROUP BY acct;
    """
    return pd.read_sql(query, con=engine)


def compute_snapshot_features(cutoff: int) -> pd.DataFrame:
    """
    Builds a strictly point-in-time graph projection and computes all 13 model features
    using ONLY transactions occurring at or before the given cutoff step.
    """
    graph_name = f"mule_graph_cutoff_{cutoff}"

    # Drop existing projection if present
    try:
        neo4j_client.execute(f"CALL gds.graph.drop('{graph_name}', false)")
    except Exception:
        pass

    # Project time-valid subgraph: only edges where t.step <= cutoff
    proj_query = f"""
    CALL gds.graph.project.cypher(
        '{graph_name}',
        'MATCH (a:Account) RETURN id(a) AS id, ["Account"] AS labels',
        'MATCH (s:Account)-[t:TRANSFER]->(r:Account) WHERE t.step <= {cutoff} RETURN id(s) AS source, id(r) AS target, "TRANSFER" AS type'
    )
    """
    neo4j_client.execute(proj_query)

    # 1. PageRank on cutoff graph
    pr_res = neo4j_client.execute(f"""
    CALL gds.pageRank.stream('{graph_name}')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).account_id AS account_id, score AS pagerank
    """)
    df_pr = pd.DataFrame([dict(r) for r in pr_res])

    # 2. Degree Centrality on cutoff graph
    deg_res = neo4j_client.execute(f"""
    CALL gds.degree.stream('{graph_name}')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).account_id AS account_id, score AS degree
    """)
    df_deg = pd.DataFrame([dict(r) for r in deg_res])

    # 3. Betweenness Centrality on cutoff graph
    bw_res = neo4j_client.execute(f"""
    CALL gds.betweenness.stream('{graph_name}')
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).account_id AS account_id, score AS betweenness
    """)
    df_bw = pd.DataFrame([dict(r) for r in bw_res])

    # 4. Louvain Community Detection on cutoff graph
    louv_res = neo4j_client.execute(f"""
    CALL gds.louvain.stream('{graph_name}')
    YIELD nodeId, communityId
    RETURN gds.util.asNode(nodeId).account_id AS account_id, communityId AS community_id
    """)
    df_louv = pd.DataFrame([dict(r) for r in louv_res])

    # Clean up projection
    neo4j_client.execute(f"CALL gds.graph.drop('{graph_name}', false)")

    # 5. Point-in-time transactional metrics (WHERE t.step <= cutoff)
    tx_query = f"""
    MATCH (a:Account)
    OPTIONAL MATCH (a)-[out:TRANSFER]->(r:Account)
    WHERE out.step <= {cutoff}
    WITH a,
         count(out) AS out_degree,
         coalesce(sum(out.amount), 0.0) AS total_sent,
         count(distinct r) AS unique_recipients
    OPTIONAL MATCH (s:Account)-[inc:TRANSFER]->(a)
    WHERE inc.step <= {cutoff}
    WITH a,
         out_degree,
         total_sent,
         unique_recipients,
         count(inc) AS in_degree,
         coalesce(sum(inc.amount), 0.0) AS total_received,
         count(distinct s) AS unique_senders
    WITH a,
         out_degree,
         in_degree,
         (out_degree + in_degree) AS transaction_count,
         total_sent,
         total_received,
         (total_sent + total_received) AS total_amount,
         unique_recipients,
         unique_senders
    RETURN
         a.account_id AS account_id,
         transaction_count,
         total_sent,
         total_received,
         case when transaction_count > 0 then total_amount / transaction_count else 0.0 end AS average_transaction_amount,
         in_degree,
         out_degree,
         unique_recipients,
         unique_senders,
         unique_recipients AS fan_out,
         unique_senders AS fan_in
    """
    tx_res = neo4j_client.execute(tx_query)
    df_tx = pd.DataFrame([dict(r) for r in tx_res])

    # Merge topological and transactional metrics
    df_merged = df_tx.merge(df_pr, on="account_id", how="left")
    df_merged = df_merged.merge(df_deg, on="account_id", how="left")
    df_merged = df_merged.merge(df_bw, on="account_id", how="left")
    df_merged = df_merged.merge(df_louv, on="account_id", how="left")

    df_merged["pagerank"] = df_merged["pagerank"].fillna(0.15).astype(float)
    df_merged["betweenness"] = df_merged["betweenness"].fillna(0.0).astype(float)
    df_merged["community_id"] = df_merged["community_id"].fillna(-1).astype(int)

    return df_merged


def build_point_in_time_dataset(output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Builds a leak-free point-in-time dataset across train (step <= 4),
    validation (step == 5), and test (step >= 6).
    """
    print("Building leak-free point-in-time feature dataset...")
    meta_df = get_account_temporal_metadata()

    train_accounts = set(meta_df[meta_df["first_step"] <= 4]["account_id"])
    val_accounts = set(meta_df[meta_df["first_step"] == 5]["account_id"])
    test_accounts = set(meta_df[meta_df["first_step"] >= 6]["account_id"])

    print(f"Partition counts: Train={len(train_accounts)}, Val={len(val_accounts)}, Test={len(test_accounts)}")

    # 1. Train snapshot: cutoff at step 4
    print("Computing features for training snapshot (step <= 4)...")
    snap4 = compute_snapshot_features(cutoff=4)
    train_feat = snap4[snap4["account_id"].isin(train_accounts)].copy()
    train_feat["split"] = "train"
    train_feat["cutoff_step"] = 4

    # 2. Validation snapshot: cutoff at step 5
    print("Computing features for validation snapshot (step <= 5)...")
    snap5 = compute_snapshot_features(cutoff=5)
    val_feat = snap5[snap5["account_id"].isin(val_accounts)].copy()
    val_feat["split"] = "val"
    val_feat["cutoff_step"] = 5

    # 3. Test snapshot: cutoff at step 7
    print("Computing features for test snapshot (step <= 7)...")
    snap7 = compute_snapshot_features(cutoff=7)
    test_feat = snap7[snap7["account_id"].isin(test_accounts)].copy()
    test_feat["split"] = "test"
    test_feat["cutoff_step"] = 7

    # Combine partitions
    all_feat = pd.concat([train_feat, val_feat, test_feat], ignore_index=True)
    all_feat = all_feat.merge(meta_df[["account_id", "first_step", "label"]], on="account_id", how="left")

    # Column ordering
    feature_cols = [
        "account_id",
        "first_step",
        "cutoff_step",
        "split",
        "transaction_count",
        "total_sent",
        "total_received",
        "average_transaction_amount",
        "in_degree",
        "out_degree",
        "pagerank",
        "betweenness",
        "community_id",
        "unique_recipients",
        "unique_senders",
        "fan_out",
        "fan_in",
        "label"
    ]
    all_feat = all_feat[feature_cols]

    if output_path is None:
        output_path = CANONICAL_FEATURES_PATH

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    all_feat.to_csv(output_path, index=False)
    all_feat.to_csv(OUTPUT_PATH, index=False)
    print(f"Point-in-time dataset successfully written to {output_path} ({len(all_feat)} rows, {len(all_feat.columns)} columns)")

    return all_feat


if __name__ == "__main__":
    build_point_in_time_dataset()
