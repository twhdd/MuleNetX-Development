from backend.neo4j_client import neo4j_client


def run_betweenness():

    query = """
    CALL gds.betweenness.write(
        'mule_graph',
        {
            writeProperty:'betweenness'
        }
    )
    """

    neo4j_client.execute(query)

    print("Betweenness Complete")


if __name__ == "__main__":
    run_betweenness()
