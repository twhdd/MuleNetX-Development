from pathlib import Path


PROMPT_FILE = Path(
    "investigation-engine/prompts/system_prompt.txt"
)


def build_prompt(context):

    system_prompt = PROMPT_FILE.read_text()

    return f"""
{system_prompt}

ACCOUNT DATA

Account ID:
{context["account_id"]}

Risk Score:
{context["risk_score"]}

PageRank:
{context["pagerank"]}

Degree:
{context["degree"]}

Betweenness:
{context["betweenness"]}

Community:
{context["community"]}

Transaction Count:
{context["transaction_count"]}

Total Sent:
{context["total_sent"]}

Connected Accounts:
{context["connected_accounts"]}
"""
