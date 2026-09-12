from graph_engine.gds_projection import create_projection
from graph_engine.pagerank import run_pagerank
from graph_engine.degree_centrality import run_degree
from graph_engine.betweenness import run_betweenness
from graph_engine.louvain import run_louvain
from graph_engine.risk_features import build_risk_features


def run():

    create_projection()

    run_pagerank()

    run_degree()

    run_betweenness()

    run_louvain()

    build_risk_features()

    print("Analytics Complete")


if __name__ == "__main__":
    run()
