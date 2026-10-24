"""Write the PaySim reference slice (SRS §7.1.2) and print the adapter_config to register it with.

Usage: python scripts/make_reference_slice.py SOURCE.csv DEST.csv [--max-rows 1000000]
Then: mulenetx ingest --path DEST.csv --name paysim-reference --dataset-version slice-v1 --adapter-config '<json>'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from mulenetx.ingestion.slice import make_slice  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--max-rows", type=int, default=1_000_000)
    args = parser.parse_args()
    config = make_slice(Path(args.source), Path(args.destination), args.max_rows)
    print(json.dumps(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
