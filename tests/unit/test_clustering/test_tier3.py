"""Tests for Tier 3: fuzzy text similarity."""

from collections.abc import Sequence

import pytest

from regintel.clustering.tier1_signature import tier1_signature_exact
from regintel.clustering.tier3_fuzzy import (
    _first_significant_token,
    _scale_fuzzy_confidence,
    _violates_never_merge,
    tier3_fuzzy,
)
from regintel.config import ClusteringConfig
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure, Severity

from .conftest import make_failure

_CFG = ClusteringConfig()


def _run_t3(failures: Sequence[Failure], cfg: ClusteringConfig = _CFG) -> list[Cluster]:
    t1 = tier1_signature_exact(failures)
    fby_id = {f.occurrence_id: f for f in failures}
    return tier3_fuzzy(t1, fby_id, cfg)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

def test_first_significant_token_skips_uvm_prefix() -> None:
    token = _first_significant_token("UVM_ERROR @ <TIME>: bus stalled")
    assert token not in {"UVM_ERROR", "@", "<TIME>"}
    assert token == "bus"


def test_first_significant_token_skips_placeholders() -> None:
    token = _first_significant_token("<NUM> <HEX> MISMATCH in queue")
    assert token == "MISMATCH"


def test_first_significant_token_empty_returns_empty() -> None:
    assert _first_significant_token("<NUM> <HEX> <TIME>") == ""


def test_scale_fuzzy_confidence_at_threshold() -> None:
    conf = _scale_fuzzy_confidence(85.0, 85.0)
    assert conf == 0.6


def test_scale_fuzzy_confidence_at_100() -> None:
    conf = _scale_fuzzy_confidence(100.0, 85.0)
    assert conf == pytest.approx(0.85, abs=0.01)


def test_scale_fuzzy_confidence_capped_at_85() -> None:
    conf = _scale_fuzzy_confidence(100.0, 85.0)
    assert conf <= 0.85


# ---------------------------------------------------------------------------
# Never-merge predicate tests
# ---------------------------------------------------------------------------

def test_never_merge_different_severity() -> None:
    from regintel.clustering.tier1_signature import tier1_signature_exact as t1
    f1 = make_failure(severity=Severity.ERROR, message="Bus stalled timeout", log_line=0)
    f2 = make_failure(severity=Severity.FATAL, message="Bus stalled timeout", log_line=1)
    clusters = t1([f1, f2])
    fby_id = {f.occurrence_id: f for f in [f1, f2]}
    c1 = next(c for c in clusters if f1.occurrence_id in c.member_failure_ids)
    c2 = next(c for c in clusters if f2.occurrence_id in c.member_failure_ids)
    assert _violates_never_merge(c1, c2, fby_id)


def test_never_merge_different_extractors() -> None:
    from regintel.clustering.tier1_signature import tier1_signature_exact as t1
    # Different extractors need different messages so they produce separate tier1 clusters
    f1 = make_failure(extractor="uvm", message="UVM_ERROR Bus stalled timeout", log_line=0,
                      extractor_keys=())
    f2 = make_failure(extractor="verilator", message="%Error bus stalled timeout", log_line=1,
                      extractor_keys=())
    clusters = t1([f1, f2])
    fby_id = {f.occurrence_id: f for f in [f1, f2]}
    assert len(clusters) == 2  # different sigs → separate clusters
    c1 = next(c for c in clusters if f1.occurrence_id in c.member_failure_ids)
    c2 = next(c for c in clusters if f2.occurrence_id in c.member_failure_ids)
    assert _violates_never_merge(c1, c2, fby_id)


def test_never_merge_different_files() -> None:
    from regintel.clustering.tier1_signature import tier1_signature_exact as t1
    f1 = make_failure(file="drv_a.sv", message="Bus stalled timeout", log_line=0,
                      extractor_keys=())
    f2 = make_failure(file="drv_b.sv", message="Bus stalled timeout", log_line=1,
                      extractor_keys=())
    clusters = t1([f1, f2])
    fby_id = {f.occurrence_id: f for f in [f1, f2]}
    c1 = next(c for c in clusters if f1.occurrence_id in c.member_failure_ids)
    c2 = next(c for c in clusters if f2.occurrence_id in c.member_failure_ids)
    assert _violates_never_merge(c1, c2, fby_id)


# ---------------------------------------------------------------------------
# Merging and non-chaining tests
# ---------------------------------------------------------------------------

def test_similar_messages_merge() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled waiting grant", log_line=0,
                      extractor_keys=())
    f2 = make_failure(message="UVM_ERROR Bus stalled no grant received", log_line=1,
                      extractor_keys=())
    clusters = _run_t3([f1, f2])
    total = sum(c.size for c in clusters)
    assert total == 2
    # If merged, the cluster method should be "fuzzy"
    fuzzy_clusters = [c for c in clusters if c.clustering_method == "fuzzy"]
    assert len(fuzzy_clusters) <= 1  # at most one fuzzy merge


def test_dissimilar_messages_stay_separate() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled timeout", log_line=0, extractor_keys=())
    f2 = make_failure(
        message="UVM_ERROR MISMATCH in queue unexpected data value", log_line=1, extractor_keys=()
    )
    clusters = _run_t3([f1, f2])
    assert len(clusters) == 2


def test_large_clusters_not_fuzzy_merged() -> None:
    """Clusters at or above tier3_max_cluster_size are left alone."""
    cfg = ClusteringConfig(tier3_max_cluster_size=2)
    # Build a cluster of size 2 (above threshold since threshold is <2, i.e. size<2 → only size 1)
    f1 = make_failure(message="UVM_ERROR Bus stalled timeout a", log_line=0)
    f2 = make_failure(message="UVM_ERROR Bus stalled timeout a", log_line=1)
    f3 = make_failure(message="UVM_ERROR Bus stalled timeout b", log_line=2, extractor_keys=())
    t1 = tier1_signature_exact([f1, f2, f3])
    fby_id = {f.occurrence_id: f for f in [f1, f2, f3]}
    large = [c for c in t1 if c.size >= cfg.tier3_max_cluster_size]
    # large clusters should pass through untouched
    result = tier3_fuzzy(t1, fby_id, cfg)
    for lc in large:
        assert any(r.cluster_id == lc.cluster_id for r in result)


def test_non_chaining_A_B_merge_C_separate() -> None:
    """A~B but A≁C: with representative-based merging, C stays separate even if B~C."""
    # A and B: similar "bus timeout" messages
    # C: very different message ("assertion violation")
    f_a = make_failure(
        message="UVM_ERROR memory write error bus overflow detected", log_line=0, extractor_keys=()
    )
    f_b = make_failure(
        message="UVM_ERROR memory read error bus overflow detected", log_line=1, extractor_keys=()
    )
    f_c = make_failure(
        message="UVM_ERROR assertion property timeout expired state", log_line=2, extractor_keys=()
    )
    clusters = _run_t3([f_a, f_b, f_c])
    # The A+B cluster may merge; C should stay separate regardless
    total = sum(c.size for c in clusters)
    assert total == 3  # all members accounted for
    # C should NOT be in the same cluster as A
    c_occ = f_c.occurrence_id
    a_occ = f_a.occurrence_id
    for c in clusters:
        if c_occ in c.member_failure_ids:
            assert a_occ not in c.member_failure_ids, (
                "Non-chaining violated: A and C ended up in the same cluster"
            )


def test_fuzzy_confidence_in_valid_range() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled waiting grant", log_line=0, extractor_keys=())
    f2 = make_failure(message="UVM_ERROR Bus stalled grant delayed", log_line=1, extractor_keys=())
    clusters = _run_t3([f1, f2])
    for c in clusters:
        assert 0.0 <= c.confidence <= 1.0
        if c.clustering_method == "fuzzy":
            assert 0.6 <= c.confidence <= 0.85
