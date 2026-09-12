import json

nodes = [
    {
        "id": "ACC-8842",
        "risk": 94,
        "state": "MH"
    },
    {
        "id": "ACC-3371",
        "risk": 87,
        "state": "DL"
    }
]

edges = [
    {
        "source": "ACC-8842",
        "target": "ACC-3371",
        "amount": 250000
    }
]

with open("data/graph.json", "w") as f:
    json.dump({
        "nodes": nodes,
        "edges": edges
    }, f, indent=2)

print("Graph exported")
