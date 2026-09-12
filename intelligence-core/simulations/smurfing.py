import random
import uuid

from backend.neo4j_client import neo4j_client


def create_smurfing_attack():

    destination = (
        f"SMURF_DEST_"
        f"{uuid.uuid4().hex[:6]}"
    )

    neo4j_client.execute(
        """
        MERGE (a:Account {
            account_id:$id
        })
        """,
        {"id": destination}
    )

    for _ in range(50):

        account = (
            f"SMURF_"
            f"{uuid.uuid4().hex[:8]}"
        )

        neo4j_client.execute(
            """
            MERGE (a:Account {
                account_id:$id
            })
            """,
            {"id": account}
        )

        neo4j_client.execute(
            """
            MATCH (a:Account {
                account_id:$src
            })

            MATCH (b:Account {
                account_id:$dst
            })

            CREATE (a)-[:TRANSFER {
                amount:$amount,
                isFraud:1
            }]->(b)
            """,
            {
                "src": account,
                "dst": destination,
                "amount": random.randint(
                    500,
                    999
                )
            }
        )

    return destination
