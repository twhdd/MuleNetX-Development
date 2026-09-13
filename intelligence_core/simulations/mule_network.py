import random
import uuid

from backend.neo4j_client import neo4j_client


def create_mule_network(
    size=20
):

    hub = f"MULE_HUB_{uuid.uuid4().hex[:6]}"

    query = """
    MERGE (a:Account {
        account_id:$id
    })
    """

    neo4j_client.execute(
        query,
        {"id": hub}
    )

    for _ in range(size):

        mule = f"MULE_{uuid.uuid4().hex[:8]}"

        neo4j_client.execute(
            query,
            {"id": mule}
        )

        rel = """
        MATCH (a:Account {
            account_id:$hub
        })

        MATCH (b:Account {
            account_id:$mule
        })

        CREATE (b)-[:TRANSFER {
            amount:$amount,
            isFraud:1
        }]->(a)
        """

        neo4j_client.execute(
            rel,
            {
                "hub": hub,
                "mule": mule,
                "amount": random.randint(
                    5000,
                    25000
                )
            }
        )

    return hub
