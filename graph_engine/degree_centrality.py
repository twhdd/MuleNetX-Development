from backend.neo4j_client import neo4j_client


def run_degree():

    query = """
    CALL gds.degree.write(
        'mule_graph',
        {
            writeProperty:'degree'
        }
    )
    """

    neo4j_client.execute(query)

    print("Degree Complete")


if __name__ == "__main__":
    run_degree()
