"""MLService training (SRS §11.4–§11.10, §12.2, §12.7; §7.6 rules 3–4).

Order: training data (T16) → normalization reference and risk logic version (created even if fitting
fails) → leakage checks 1–5, 7 → fit on the training split → threshold on validation (max F1) → metrics on
validation and test → leakage check 6 → artifact + SHA-256 → model registration.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
from sqlalchemy.dialects.postgresql import insert

from mulenetx.core.decimal import D, round7
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import ModelVersion, RiskLogicVersion
from mulenetx.features.registry import FEATURE_REGIME
from mulenetx.features.registry import load as load_registry
from mulenetx.ml import leakage
from mulenetx.ml.artifacts import artifact_path, sha256_file
from mulenetx.ml.dataset_builder import TrainingData, build, label_window_audit
from mulenetx.ml.metrics import evaluate, max_f1_threshold
from mulenetx.ml.model import MODEL_TYPE, XGBoostModel, hyperparameters, implementation_version
from mulenetx.ml.target import target_definition
from mulenetx.risk import normalization_reference
from mulenetx.risk.config import risk_logic_content, risk_logic_version_name

logger = logging.getLogger("mulenetx.ml")


@dataclass
class TrainingOutcome:
    model_version: str | None
    risk_logic_version: str
    training_snapshot_ids: list[uuid.UUID] = field(default_factory=list)
    failure_reason: str | None = None
    leakage_checks: list[dict[str, Any]] = field(default_factory=list)
    test_predictions: dict[str, float] = field(default_factory=dict)


def _json_params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: ("NaN" if isinstance(v, float) and v != v else v) for k, v in params.items()}


def create_risk_logic_version(rt: Runtime, reference: dict[str, Any]) -> str:
    content = risk_logic_content(rt.settings)
    name = risk_logic_version_name(content, reference)
    with rt.session_factory() as db:
        db.execute(
            insert(RiskLogicVersion)
            .values(
                risk_logic_version=name,
                formula_identifier=content["formula_identifier"],
                configuration=content["configuration"],
                normalization_reference=reference,
                rules=content["rules"],
                tier_thresholds=content["tier_thresholds"],
                propagation_parameters=content["propagation_parameters"],
                ring_parameters=content["ring_parameters"],
                created_at=utcnow(),
            )
            .on_conflict_do_nothing()
        )
        db.commit()
    return name


def model_version_name(created: datetime, sha: str) -> str:
    """Unique per registration (two trainings can produce byte-identical artifacts, §11.9)."""
    return f"xgb-{created:%Y%m%dT%H%M%S}-{sha[:8]}-{uuid.uuid4().hex[:6]}"


class TrainingService:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime

    def train(
        self, dataset_id: uuid.UUID, ingestion_run_id: uuid.UUID, resolution: int, check: Any = None
    ) -> TrainingOutcome:
        reg = load_registry()
        data = build(self.rt, dataset_id, ingestion_run_id, resolution, check)
        snapshots = [s.graph_snapshot_id for s in data.splits.values()]
        train = data.splits["train"]
        model_tag = str(uuid.uuid4())  # placeholder link until the model is registered
        reference = normalization_reference.build(reg.ids, train.features, train.states)
        pre = [
            leakage.check_1_feature_event_time(data),
            leakage.check_2_graph_snapshot_cutoff(data),
            leakage.check_3_entity_separation(data),
            leakage.check_4_no_label_columns(reg),
            leakage.check_5_regime(data, reg),
            leakage.check_7_label_window(data, label_window_audit(self.rt, data)),
        ]
        failure = self._failure(pre, data)
        if failure is not None:
            reference = {**reference, "model_version": None, "training_failure": failure}
            rl = create_risk_logic_version(self.rt, reference)
            return TrainingOutcome(None, rl, snapshots, failure, [c.__dict__ for c in pre])

        y_train = np.array(train.labels, dtype=np.int32)
        positives = int(y_train.sum())
        scale_pos_weight = (len(y_train) - positives) / positives
        params = hyperparameters(self.rt.settings, float(scale_pos_weight))
        model = XGBoostModel(params)
        model.train(train.features, y_train)
        val, test = data.splits["val"], data.splits["test"]
        val_scores = model.predict(val.features) if len(val.labels) else np.zeros(0)
        y_val = np.array(val.labels, dtype=np.int32)
        threshold = max_f1_threshold(y_val, val_scores) if len(y_val) and 0 < y_val.sum() < len(y_val) else 0.5
        test_scores = model.predict(test.features) if len(test.labels) else np.zeros(0)
        y_test = np.array(test.labels, dtype=np.int32)
        post = leakage.check_6_test_not_used(set(train.accounts), set(), data)
        checks = [*pre, post]
        if not post.passed:
            failure = f"leakage check failed: {post.check}"
            reference = {**reference, "model_version": None, "training_failure": failure}
            rl = create_risk_logic_version(self.rt, reference)
            return TrainingOutcome(None, rl, snapshots, failure, [c.__dict__ for c in checks])

        created = utcnow()
        tmp = artifact_path(self.rt.settings.artifact_dir, f"tmp-{model_tag}")
        model.save(tmp)
        sha = sha256_file(tmp)
        version = model_version_name(created, sha)
        final = artifact_path(self.rt.settings.artifact_dir, version)
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp.replace(final)
        tmp.parent.rmdir()
        reference = {**reference, "model_version": version}
        rl = create_risk_logic_version(self.rt, reference)
        metrics = {
            "validation": evaluate(y_val, val_scores, val.accounts, threshold),
            "test": evaluate(y_test, test_scores, test.accounts, threshold),
            "operating_threshold_rule": "maximize F1 on the validation split",
            "leakage_checks": [c.__dict__ for c in checks],
        }
        with self.rt.session_factory() as db:
            db.add(
                ModelVersion(
                    model_version=version,
                    model_type=MODEL_TYPE,
                    target_definition=target_definition(data.boundaries.window_table()),
                    feature_version=data.feature_version,
                    feature_regime=FEATURE_REGIME,
                    training_dataset_id=dataset_id,
                    training_snapshot_ids={s.split: str(s.graph_snapshot_id) for s in data.splits.values()},
                    split_boundaries=data.boundaries.as_json(),
                    training_config={
                        "hyperparameters": _json_params(params),
                        "class_weight": {
                            "scale_pos_weight": scale_pos_weight,
                            "rule": "negatives / positives (training)",
                        },
                        "feature_snapshot_ids": {s.split: str(s.feature_snapshot_id) for s in data.splits.values()},
                        "risk_logic_version": rl,
                    },
                    class_distribution={
                        s.split: {**s.class_distribution(), "exclusions": s.exclusions} for s in data.splits.values()
                    },
                    evaluation_metrics=json.loads(json.dumps(metrics, default=float)),
                    operating_threshold=round7(D(threshold)),
                    artifact_reference=str(final),
                    artifact_sha256=sha,
                    implementation_version=implementation_version(),
                    random_seed=self.rt.settings.xgb_random_seed,
                    created_at=created,
                )
            )
            db.commit()
        predictions = {a: float(p) for a, p in zip(test.accounts, test_scores, strict=True)}
        return TrainingOutcome(version, rl, snapshots, None, [c.__dict__ for c in checks], predictions)

    @staticmethod
    def _failure(checks: list[leakage.CheckResult], data: TrainingData) -> str | None:
        failed = [c.check for c in checks if not c.passed]
        if failed:
            return f"leakage checks failed: {', '.join(failed)}"
        labels = data.splits["train"].labels
        if not labels or sum(labels) == 0 or sum(labels) == len(labels):
            return "the training split needs both positive and negative observations"
        return None
