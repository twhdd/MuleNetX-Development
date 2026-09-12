from backend.neo4j_client import neo4j_client


def create_projection():

    drop_query = """
    CALL gds.graph.drop(
        'mule_graph',
        false
    )
    """

    try:
        neo4j_client.execute(drop_query)
    except:
        pass

    query = """
    CALL gds.graph.project(
        'mule_graph',
        'Account',
        {
            TRANSFER: {
                orientation: 'NATURAL'
            }
        }
    )
    """

    neo4j_client.execute(query)

    print("Projection Created")


if __name__ == "__main__":
    create_projection()
