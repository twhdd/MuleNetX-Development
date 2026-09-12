import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml_engine.train_model import run_training_pipeline
from ml_engine.write_scores import write_scores


def main():
    results = run_training_pipeline()
    print("\n--- Writing Risk Scores to Neo4j Graph ---")
    write_scores()
    print("\nPhase 3 execution complete.")
    return results


if __name__ == "__main__":
    main()
