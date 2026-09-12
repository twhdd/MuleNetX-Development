from backend.neo4j_client import neo4j_client


def create_schema():

    query_constraint = """
    CREATE CONSTRAINT account_id_unique IF NOT EXISTS
    FOR (a:Account)
    REQUIRE a.account_id IS UNIQUE
    """

    query_index = """
    CREATE INDEX account_id_index IF NOT EXISTS
    FOR (a:Account)
    ON (a.account_id)
    """

    neo4j_client.execute(query_constraint)
    try:
        neo4j_client.execute(query_index)
    except Exception:
        pass

    print("Schema created")


if __name__ == "__main__":
    create_schema()
