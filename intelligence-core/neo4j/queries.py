from connection import get_driver

def create_account(account_id):

    query = """
    MERGE (a:Account {account_id:$id})
    RETURN a
    """

    with get_driver().session() as session:
        session.run(query,id=account_id)

def create_transaction(sender,receiver,amount):

    query = """
    MERGE (s:Account {account_id:$sender})
    MERGE (r:Account {account_id:$receiver})

    MERGE (s)-[:TRANSFERRED {
        amount:$amount
    }]->(r)
    """

    with get_driver().session() as session:
        session.run(
            query,
            sender=sender,
            receiver=receiver,
            amount=amount
        )
