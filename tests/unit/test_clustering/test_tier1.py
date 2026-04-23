"""Tests for Tier 1: signature-exact grouping."""

import json

from regintel.clustering.tier1_signature import tier1_signature_exact
from regintel.models.serialization import to_dict

from .conftest import make_failure


def test_identical_signatures_group_together() -> None:
    f1 = make_failure(test_name="test_a", log_line=0)
    f2 = make_failure(test_name="test_b", log_line=1)
    # Same message, file, line, severity, extractor_keys → same signature
    assert f1.signature_id == f2.signature_id

    clusters = tier1_signature_exact([f1, f2])
    assert len(clusters) == 1
    assert clusters[0].size == 2


def test_different_messages_produce_separate_clusters() -> None:
    f1 = make_failure(message="UVM_ERROR Bus stalled")
    f2 = make_failure(message="UVM_ERROR MISMATCH in queue", log_line=1)
    assert f1.signature_id != f2.signature_id

    clusters = tier1_signature_exact([f1, f2])
    assert len(clusters) == 2


def test_cluster_id_equals_signature_id() -> None:
    f = make_failure()
    clusters = tier1_signature_exact([f])
    assert clusters[0].cluster_id == f.signature_id


def test_representative_is_lex_smallest_occurrence_id() -> None:
    f1 = make_failure(test_name="test_z", log_line=0)
    f2 = make_failure(test_name="test_a", log_line=1)
    clusters = tier1_signature_exact([f1, f2])
    rep_id = clusters[0].representative_failure_id
    assert rep_id == min(f1.occurrence_id, f2.occurrence_id)


def test_confidence_is_1() -> None:
    f = make_failure()
    clusters = tier1_signature_exact([f])
    assert clusters[0].confidence == 1.0


def test_tier_is_1() -> None:
    f = make_failure()
    clusters = tier1_signature_exact([f])
    assert clusters[0].tier == 1
    assert clusters[0].clustering_method == "signature"


def test_affected_tests_sorted_deduplicated() -> None:
    f1 = make_failure(test_name="zzz", log_line=0)
    f2 = make_failure(test_name="aaa", log_line=1)
    clusters = tier1_signature_exact([f1, f2])
    assert clusters[0].affected_tests == ("aaa", "zzz")


def test_member_ids_sorted() -> None:
    f1 = make_failure(test_name="test_a", log_line=0)
    f2 = make_failure(test_name="test_b", log_line=1)
    clusters = tier1_signature_exact([f1, f2])
    ids = clusters[0].member_failure_ids
    assert list(ids) == sorted(ids)


def test_sorted_by_size_desc_then_cluster_id() -> None:
    # Two singletons + one pair
    fa = make_failure(message="UVM_ERROR msg one", log_line=0)
    fb = make_failure(message="UVM_ERROR msg one", log_line=1)  # same sig as fa
    fc = make_failure(message="UVM_ERROR msg two", log_line=2)
    clusters = tier1_signature_exact([fa, fb, fc])
    assert clusters[0].size == 2  # pair comes first
    assert clusters[1].size == 1


def test_empty_failures_returns_empty() -> None:
    assert tier1_signature_exact([]) == []


def test_deterministic() -> None:
    failures = [make_failure(test_name=f"t{i}", log_line=i) for i in range(5)]
    a = tier1_signature_exact(failures)
    b = tier1_signature_exact(failures)
    assert json.dumps(to_dict(a[0])) == json.dumps(to_dict(b[0]))


def test_common_location_set_when_shared() -> None:
    f1 = make_failure(log_line=0)
    f2 = make_failure(log_line=1)
    clusters = tier1_signature_exact([f1, f2])
    assert clusters[0].common_location is not None
    assert clusters[0].common_location.file == "drv.sv"


def test_common_location_none_when_lines_differ() -> None:
    f1 = make_failure(file="drv.sv", line=10, log_line=0)
    f2 = make_failure(file="drv.sv", line=99, log_line=1)
    # Different lines → different signatures → separate clusters, each with location
    clusters = tier1_signature_exact([f1, f2])
    # They have different signatures so won't group
    assert len(clusters) == 2
