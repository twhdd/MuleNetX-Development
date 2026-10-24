"""AT-INT-07: a simulation never recomputes PageRank, betweenness, communities, graph construction, training,
SHAP or inference (§16A.7): the intervention package imports none of that code and filters the baseline only."""

import ast
from pathlib import Path

import mulenetx.interventions as package

FORBIDDEN = (
    "mulenetx.analytics",
    "mulenetx.ml",
    "mulenetx.explain",
    "mulenetx.risk",
    "mulenetx.features",
    "mulenetx.graph",
    "mulenetx.propagation",
    "mulenetx.motifs",
    "networkx",
    "xgboost",
    "neo4j",
)
PURE = ("baseline.py", "pool.py", "residual.py", "metrics.py", "ranking.py", "engine.py")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_AT_INT_07_no_prohibited_imports() -> None:
    root = Path(package.__file__).parent
    for path in sorted(root.glob("*.py")):
        for module in _imports(path):
            assert not module.startswith(FORBIDDEN), f"{path.name} imports {module}"


def test_AT_INT_07_engine_is_pure() -> None:
    root = Path(package.__file__).parent
    for name in PURE:
        mods = _imports(root / name)
        assert not any(m.startswith(("sqlalchemy", "mulenetx.db", "mulenetx.jobs")) for m in mods), (name, mods)
