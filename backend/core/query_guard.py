DANGEROUS = [
    "DETACH DELETE",
    "DELETE",
    "DROP",
    "REMOVE",
    "CALL dbms"
]


def validate_query(
    query
):

    upper = query.upper()

    for item in DANGEROUS:

        if item in upper:
            if item == "DROP" and "GDS.GRAPH.DROP" in upper:
                continue
            raise Exception(
                f"Blocked Query: {item}"
            )
