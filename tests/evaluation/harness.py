"""Evaluation harness runner.

Loads the labeled corpus from tests/evaluation/labeled/,
runs RegIntel's extraction and clustering pipeline,
computes clustering quality metrics, and returns a summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from regintel.clustering.cascade import cluster_failures
from regintel.config import ClusteringConfig
from regintel.ingestion.loader import load_run
from tests.evaluation.metrics import (
    ClusteringMetrics,
    aggregate,
    compute_metrics,
)

_LABELED_DIR = Path(__file__).parent / "labeled"
_DEFAULT_CONFIG = ClusteringConfig()


@dataclass
class RunResult:
    description: str
    manifest_path: Path
    metrics: ClusteringMetrics
    n_unmatched: int  # failures not in ground truth


@dataclass
class EvaluationReport:
    run_results: list[RunResult]
    aggregate_metrics: ClusteringMetrics

    def passed(self) -> bool:
        return self.aggregate_metrics.passes_gate()

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        print("RegIntel Evaluation Harness")
        print("=" * 70)
        for r in self.run_results:
            gate = "✓" if r.metrics.passes_gate() else "✗"
            print(f"\n  [{gate}] {r.description}")
            print(f"      manifest: {r.manifest_path}")
            print(f"      {r.metrics.summary()}")
            if r.n_unmatched > 0:
                print(f"      NOTE: {r.n_unmatched} failures had no GT label (skipped)")

        print("\n" + "-" * 70)
        agg = self.aggregate_metrics
        gate = "PASS" if agg.passes_gate() else "FAIL"
        print(f"  AGGREGATE [{gate}]: {agg.summary()}")
        print("=" * 70 + "\n")

    def print_diagnostics(self) -> None:
        for r in self.run_results:
            if not r.metrics.passes_gate():
                print(f"\nDiagnostics for: {r.description}")
                print("  (re-running to get per-cluster breakdown)")


def _load_labeled_run(gt_path: Path) -> RunResult:
    raw: dict[str, Any] = json.loads(gt_path.read_text(encoding="utf-8"))
    description: str = raw["description"]
    manifest_rel: str = raw["manifest_path"]
    manifest_path = (gt_path.parent / manifest_rel).resolve()

    # Build test_name → gt_label mapping
    test_to_gt: dict[str, str] = {}
    for cluster_spec in raw["ground_truth_clusters"]:
        label: str = cluster_spec["label"]
        for test_name in cluster_spec["member_test_names"]:
            test_to_gt[test_name] = label

    # Run extraction
    _run, failures = load_run(manifest_path)
    if not failures:
        return RunResult(
            description=description,
            manifest_path=manifest_path,
            metrics=ClusteringMetrics(1.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0),
            n_unmatched=0,
        )

    # Run clustering
    clusters = cluster_failures(failures, _DEFAULT_CONFIG)

    # Build predicted map: occurrence_id → cluster_id
    predicted: dict[str, str] = {}
    for c in clusters:
        for mid in c.member_failure_ids:
            predicted[mid] = c.cluster_id

    # Build ground truth map: occurrence_id → gt_label
    ground_truth: dict[str, str] = {}
    n_unmatched = 0
    for f in failures:
        if f.test_name in test_to_gt:
            ground_truth[f.occurrence_id] = test_to_gt[f.test_name]
        else:
            n_unmatched += 1

    metrics = compute_metrics(ground_truth, predicted)
    return RunResult(
        description=description,
        manifest_path=manifest_path,
        metrics=metrics,
        n_unmatched=n_unmatched,
    )


def run_evaluation(labeled_dir: Path = _LABELED_DIR) -> EvaluationReport:
    gt_files = sorted(labeled_dir.glob("*.json"))
    if not gt_files:
        raise FileNotFoundError(f"No ground truth JSON files found in {labeled_dir}")

    results: list[RunResult] = []
    for gt_path in gt_files:
        result = _load_labeled_run(gt_path)
        results.append(result)

    agg = aggregate([r.metrics for r in results])
    return EvaluationReport(run_results=results, aggregate_metrics=agg)


if __name__ == "__main__":
    report = run_evaluation()
    report.print_summary()
    if not report.passed():
        report.print_diagnostics()
        raise SystemExit(1)
