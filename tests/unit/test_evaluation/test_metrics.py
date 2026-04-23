"""Unit tests for the evaluation metrics module."""

import pytest

from tests.evaluation.metrics import ClusteringMetrics, aggregate, compute_metrics


def test_perfect_clustering() -> None:
    gt = {"a": "bug1", "b": "bug1", "c": "bug2"}
    pred = {"a": "c1", "b": "c1", "c": "c2"}
    m = compute_metrics(gt, pred)
    assert m.pairwise_precision == 1.0
    assert m.pairwise_recall == 1.0
    assert m.pairwise_f1 == 1.0
    assert m.weighted_purity == 1.0
    assert m.weighted_completeness == 1.0


def test_all_in_one_cluster() -> None:
    # All failures in one predicted cluster, but two GT clusters → low precision
    gt = {"a": "bug1", "b": "bug1", "c": "bug2", "d": "bug2"}
    pred = {"a": "c1", "b": "c1", "c": "c1", "d": "c1"}
    m = compute_metrics(gt, pred)
    # TP=2 (aa+bb and cc+dd pairs), FP=4 (cross-GT pairs merged), FN=0
    # P=2/6=0.33, R=1.0
    assert m.pairwise_recall == 1.0
    assert m.pairwise_precision < 0.5
    assert m.weighted_purity == 0.5  # dominant GT class = 2/4


def test_all_singletons() -> None:
    # Every failure in its own cluster → zero recall
    gt = {"a": "bug1", "b": "bug1", "c": "bug2"}
    pred = {"a": "c1", "b": "c2", "c": "c3"}
    m = compute_metrics(gt, pred)
    # TP=0, FP=0, FN=1 (a-b pair in same GT but different pred)
    assert m.pairwise_recall == 0.0
    assert m.pairwise_precision == 1.0  # no false positives
    assert m.weighted_purity == 1.0  # each pred cluster is pure
    assert m.weighted_completeness < 1.0  # GT clusters are split


def test_empty_returns_perfect() -> None:
    m = compute_metrics({}, {})
    assert m.pairwise_f1 == 1.0
    assert m.n_failures == 0


def test_only_common_ids_used() -> None:
    gt = {"a": "bug1", "b": "bug1", "extra": "bug2"}  # 'extra' not in pred
    pred = {"a": "c1", "b": "c1"}
    m = compute_metrics(gt, pred)
    assert m.n_failures == 2  # only a and b
    assert m.pairwise_f1 == 1.0


def test_n_clusters_correct() -> None:
    gt = {"a": "bug1", "b": "bug1", "c": "bug2", "d": "bug2"}
    pred = {"a": "c1", "b": "c1", "c": "c2", "d": "c2"}
    m = compute_metrics(gt, pred)
    assert m.n_gt_clusters == 2
    assert m.n_pred_clusters == 2


def test_passes_gate() -> None:
    m = ClusteringMetrics(
        pairwise_precision=0.9,
        pairwise_recall=0.9,
        pairwise_f1=0.9,
        weighted_purity=0.9,
        weighted_completeness=0.9,
        n_failures=10,
        n_pred_clusters=2,
        n_gt_clusters=2,
    )
    assert m.passes_gate()


def test_fails_gate_low_f1() -> None:
    m = ClusteringMetrics(
        pairwise_precision=0.7,
        pairwise_recall=0.7,
        pairwise_f1=0.7,
        weighted_purity=0.9,
        weighted_completeness=0.9,
        n_failures=10,
        n_pred_clusters=2,
        n_gt_clusters=2,
    )
    assert not m.passes_gate()


def test_aggregate_weighted_by_failures() -> None:
    m1 = ClusteringMetrics(1.0, 1.0, 1.0, 1.0, 1.0, n_failures=8,
                           n_pred_clusters=2, n_gt_clusters=2)
    m2 = ClusteringMetrics(0.0, 0.0, 0.0, 0.0, 0.0, n_failures=2,
                           n_pred_clusters=1, n_gt_clusters=2)
    agg = aggregate([m1, m2])
    # weighted F1 = (1.0*8 + 0.0*2) / 10 = 0.8
    assert agg.pairwise_f1 == pytest.approx(0.8, abs=0.01)
    assert agg.n_failures == 10


def test_aggregate_empty() -> None:
    agg = aggregate([])
    assert agg.pairwise_f1 == 1.0
    assert agg.n_failures == 0
