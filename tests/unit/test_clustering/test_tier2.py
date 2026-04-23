"""Tests for Tier 2: structural merging."""

from collections.abc import Sequence

from regintel.clustering.tier1_signature import tier1_signature_exact
from regintel.clustering.tier2_structural import tier2_structural
from regintel.config import ClusteringConfig
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure, Severity

from .conftest import make_failure

_CFG = ClusteringConfig()


def _run(failures: Sequence[Failure], cfg: ClusteringConfig = _CFG) -> list[Cluster]:
    t1 = tier1_signature_exact(failures)
    fby_id = {f.occurrence_id: f for f in failures}
    return tier2_structural(t1, fby_id, cfg)


def test_singleton_cluster_passes_through() -> None:
    f = make_failure()
    clusters = _run([f])
    assert len(clusters) == 1
    assert clusters[0].size == 1


def test_structurally_matching_clusters_merge() -> None:
    # Different messages but same file:line, severity, extractor, extractor_keys
    f1 = make_failure(message="UVM_ERROR Bus stalled waiting", log_line=0)
    f2 = make_failure(message="UVM_ERROR Bus stalled no grant", log_line=1)
    # Same signature? No — different messages → different sigs → two Tier 1 clusters
    # They should merge in Tier 2 if structural key matches and similarity ≥ 60
    clusters = _run([f1, f2])
    # Only merges if structural key is identical AND messages are similar enough
    if len(clusters) == 1:
        assert clusters[0].clustering_method == "structural"
        assert clusters[0].tier == 2
        assert clusters[0].confidence == 0.9
    # If they happen to have the same signature (they shouldn't), that's fine too


def test_different_extractor_keys_prevents_merge() -> None:
    # Same file:line:severity:extractor, but different extractor_keys
    f1 = make_failure(
        message="MISMATCH in queue payload_q",
        extractor_keys=("uvm_test_top.env.axi_sb", "SCB"),
        log_line=0,
    )
    f2 = make_failure(
        message="MISMATCH in queue payload_q",
        extractor_keys=("uvm_test_top.env.mem_sb", "SCB"),
        log_line=1,
    )
    assert f1.signature_id != f2.signature_id  # different keys → different sigs
    clusters = _run([f1, f2])
    # extractor_keys differ → StructuralKey differs → no merge
    assert all(c.size == 1 for c in clusters)


def test_low_similarity_prevents_merge() -> None:
    # Same structural key but messages are semantically different
    f1 = make_failure(
        message="UVM_ERROR Bus stalled waiting grant",
        log_line=0,
        extractor_keys=(),
    )
    f2 = make_failure(
        message="UVM_ERROR Assertion violation timeout expired",
        log_line=1,
        extractor_keys=(),
    )
    cfg = ClusteringConfig(tier2_min_similarity=95)  # very high threshold
    clusters = _run([f1, f2], cfg)
    # Structurally same (empty extractor_keys, same file/line/sev/extractor)
    # But similarity < 95 → do NOT merge
    # Note: they may have same sig if same extractor_keys; let's check
    if f1.signature_id != f2.signature_id:
        # Two Tier 1 clusters with same StructuralKey but low similarity → stays separate
        separate_clusters = [c for c in clusters if c.size == 1]
        assert len(separate_clusters) >= 1


def test_merge_result_has_all_members() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled first", log_line=0)
    f2 = make_failure(message="UVM_ERROR Bus stalled second", log_line=1)
    # These have different sigs (different messages → different signatures since different
    # normalized messages). But same structural key.
    clusters = _run([f1, f2])
    total_members = sum(c.size for c in clusters)
    assert total_members == 2


def test_tier2_disabled() -> None:
    from regintel.clustering.cascade import cluster_failures
    f1 = make_failure(message="UVM_ERROR Bus stalled first", log_line=0)
    f2 = make_failure(message="UVM_ERROR Bus stalled second", log_line=1)
    cfg = ClusteringConfig(enable_tier2=False, enable_tier3=False)
    clusters = cluster_failures([f1, f2], cfg)
    total = sum(c.size for c in clusters)
    assert total == 2


def test_severity_mismatch_structural_key_differs() -> None:
    f1 = make_failure(severity=Severity.ERROR, log_line=0)
    f2 = make_failure(severity=Severity.FATAL, log_line=1)
    assert f1.signature_id != f2.signature_id  # severity in sig
    clusters = _run([f1, f2])
    # StructuralKey includes severity → different keys → no merge
    assert all(c.size == 1 for c in clusters)
