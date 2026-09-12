from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

query = """
CALL gds.pageRank.stream('transactionGraph')
YIELD nodeId, score

RETURN
gds.util.asNode(nodeId).account_id AS account,
score

ORDER BY score DESC
LIMIT 20
"""

with driver.session() as session:

    result = session.run(query)

    for row in result:
        print(row["account"], row["score"])
