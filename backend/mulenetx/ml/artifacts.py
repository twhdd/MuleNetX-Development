"""Model artifacts on the artifact volume: `ARTIFACT_DIR/<model_version>/model.json` with SHA-256."""

from __future__ import annotations

import hashlib
from pathlib import Path


def artifact_path(artifact_dir: str, model_version: str) -> Path:
    return Path(artifact_dir) / model_version / "model.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()
