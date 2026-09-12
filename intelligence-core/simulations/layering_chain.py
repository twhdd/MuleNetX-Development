import uuid

from backend.neo4j_client import neo4j_client


def create_layering_chain():

    accounts = []

    for _ in range(10):

        account = (
            f"LAYER_"
            f"{uuid.uuid4().hex[:6]}"
        )

        accounts.append(
            account
        )

        neo4j_client.execute(
            """
            MERGE (a:Account {
                account_id:$id
            })
            """,
            {"id": account}
        )

    for i in range(
        len(accounts)-1
    ):

        neo4j_client.execute(
            """
            MATCH (a:Account {
                account_id:$src
            })

            MATCH (b:Account {
                account_id:$dst
            })

            CREATE (a)-[:TRANSFER {
                amount:10000,
                isFraud:1
            }]->(b)
            """,
            {
                "src": accounts[i],
                "dst": accounts[i+1]
            }
        )

    return accounts
