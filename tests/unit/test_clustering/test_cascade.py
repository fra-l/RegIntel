"""Tests for the full clustering cascade."""

import json

from regintel.clustering.cascade import cluster_failures
from regintel.config import ClusteringConfig
from regintel.models.serialization import to_dict

from .conftest import make_failure

_CFG = ClusteringConfig()


def test_empty_failures_returns_empty() -> None:
    assert cluster_failures([], _CFG) == []


def test_single_failure_produces_one_cluster() -> None:
    f = make_failure()
    clusters = cluster_failures([f], _CFG)
    assert len(clusters) == 1
    assert clusters[0].size == 1


def test_same_signature_groups_tier1() -> None:
    f1 = make_failure(log_line=0)
    f2 = make_failure(log_line=1)
    clusters = cluster_failures([f1, f2], _CFG)
    assert len(clusters) == 1
    assert clusters[0].size == 2


def test_output_sorted_by_size_desc() -> None:
    f1 = make_failure(message="UVM_ERROR one failure", log_line=0, extractor_keys=())
    f2 = make_failure(message="UVM_ERROR two failures a", log_line=1, extractor_keys=())
    f3 = make_failure(message="UVM_ERROR two failures a", log_line=2, extractor_keys=())
    clusters = cluster_failures([f1, f2, f3], _CFG)
    sizes = [c.size for c in clusters]
    assert sizes == sorted(sizes, reverse=True)


def test_tier2_disabled_config() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled first", log_line=0)
    f2 = make_failure(message="UVM_ERROR Bus stalled second", log_line=1)
    cfg = ClusteringConfig(enable_tier2=False, enable_tier3=False)
    clusters = cluster_failures([f1, f2], cfg)
    # Only tier1 runs — each unique signature is its own cluster
    total_members = sum(c.size for c in clusters)
    assert total_members == 2


def test_tier3_disabled_config() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled first", log_line=0, extractor_keys=())
    f2 = make_failure(message="UVM_ERROR Bus stalled second", log_line=1, extractor_keys=())
    cfg = ClusteringConfig(enable_tier3=False)
    clusters = cluster_failures([f1, f2], cfg)
    total_members = sum(c.size for c in clusters)
    assert total_members == 2


def test_all_member_ids_accounted_for() -> None:
    failures = [make_failure(log_line=i) for i in range(5)]
    clusters = cluster_failures(failures, _CFG)
    all_ids = {f.occurrence_id for f in failures}
    clustered_ids = {mid for c in clusters for mid in c.member_failure_ids}
    assert all_ids == clustered_ids


def test_deterministic_byte_identical() -> None:
    """Same failures → byte-identical JSON output across two runs."""
    failures = [
        make_failure(message="UVM_ERROR msg alpha", log_line=0, extractor_keys=()),
        make_failure(message="UVM_ERROR msg alpha", log_line=1, extractor_keys=()),
        make_failure(message="UVM_ERROR msg beta", log_line=2, extractor_keys=()),
    ]
    a = cluster_failures(failures, _CFG)
    b = cluster_failures(failures, _CFG)

    assert len(a) == len(b)
    for ca, cb in zip(a, b, strict=True):
        assert json.dumps(to_dict(ca)) == json.dumps(to_dict(cb))


def test_cross_run_annotations_empty_in_mvp() -> None:
    f = make_failure()
    clusters = cluster_failures([f], _CFG)
    assert dict(clusters[0].cross_run_annotations) == {}
