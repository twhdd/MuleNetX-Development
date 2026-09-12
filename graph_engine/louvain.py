from backend.neo4j_client import neo4j_client


def run_louvain():

    query = """
    CALL gds.louvain.write(
        'mule_graph',
        {
            writeProperty:'community'
        }
    )
    """

    neo4j_client.execute(query)

    print("Communities Generated")


if __name__ == "__main__":
    run_louvain()
