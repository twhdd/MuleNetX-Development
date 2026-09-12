import uuid

from backend.neo4j_client import neo4j_client


def create_ring():

    nodes = []

    for _ in range(12):

        account = (
            f"RING_"
            f"{uuid.uuid4().hex[:6]}"
        )

        nodes.append(
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
        len(nodes)
    ):

        src = nodes[i]

        dst = nodes[
            (i+1) % len(nodes)
        ]

        neo4j_client.execute(
            """
            MATCH (a:Account {
                account_id:$src
            })

            MATCH (b:Account {
                account_id:$dst
            })

            CREATE (a)-[:TRANSFER {
                amount:25000,
                isFraud:1
            }]->(b)
            """,
            {
                "src": src,
                "dst": dst
            }
        )

    return nodes
