from backend.neo4j_client import neo4j_client


def run_pagerank():

    query = """
    CALL gds.pageRank.write(
        'mule_graph',
        {
            writeProperty: 'pagerank'
        }
    )
    """

    neo4j_client.execute(query)

    print("PageRank Complete")


if __name__ == "__main__":
    run_pagerank()
