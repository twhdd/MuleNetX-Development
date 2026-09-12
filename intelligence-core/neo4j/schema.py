from connection import get_driver

def create_constraints():

    query = """
    CREATE CONSTRAINT account_id IF NOT EXISTS
    FOR (a:Account)
    REQUIRE a.account_id IS UNIQUE
    """

    with get_driver().session() as session:
        session.run(query)

    print("Schema initialized")
