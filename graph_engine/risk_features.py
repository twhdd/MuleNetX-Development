from backend.neo4j_client import neo4j_client


def build_risk_features():
    query = """
    MATCH (a:Account)
    OPTIONAL MATCH (a)-[out:TRANSFER]->(r:Account)
    WITH a,
         count(out) AS out_degree,
         coalesce(sum(out.amount), 0.0) AS total_sent,
         count(distinct r) AS unique_recipients,
         sum(case when out.isFraud = 1 then 1 else 0 end) AS out_fraud_cnt,
         max(coalesce(out.isFraud, 0)) AS out_max_fraud
    OPTIONAL MATCH (s:Account)-[inc:TRANSFER]->(a)
    WITH a,
         out_degree,
         total_sent,
         unique_recipients,
         out_fraud_cnt,
         out_max_fraud,
         count(inc) AS in_degree,
         coalesce(sum(inc.amount), 0.0) AS total_received,
         count(distinct s) AS unique_senders,
         sum(case when inc.isFraud = 1 then 1 else 0 end) AS in_fraud_cnt,
         max(coalesce(inc.isFraud, 0)) AS in_max_fraud
    WITH a,
         out_degree,
         in_degree,
         (out_degree + in_degree) AS tx_count,
         total_sent,
         total_received,
         (total_sent + total_received) AS total_amount,
         unique_recipients,
         unique_senders,
         (out_fraud_cnt + in_fraud_cnt) AS fraud_tx_count,
         case when (out_max_fraud = 1 or in_max_fraud = 1) then 1 else 0 end AS fraud_label
    SET
        a.out_degree = out_degree,
        a.in_degree = in_degree,
        a.tx_count = tx_count,
        a.total_sent = total_sent,
        a.total_received = total_received,
        a.avg_tx_amount = case when tx_count > 0 then total_amount / tx_count else 0.0 end,
        a.unique_recipients = unique_recipients,
        a.unique_senders = unique_senders,
        a.fan_out = unique_recipients,
        a.fan_in = unique_senders,
        a.fraud_count = fraud_tx_count,
        a.fraud_ratio = case when tx_count > 0 then toFloat(fraud_tx_count) / tx_count else 0.0 end,
        a.is_fraud = fraud_label
    """

    neo4j_client.execute(query)
    print("Risk Features Generated")


if __name__ == "__main__":
    build_risk_features()
