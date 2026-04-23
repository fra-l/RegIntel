"""Round-trip tests: to_dict(instance) → from_dict → must equal original."""

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from regintel.models import (
    AnalysisReport,
    Cluster,
    Failure,
    FlakyTest,
    Run,
    Severity,
    SourceLocation,
    TestResult,
    TestStatus,
    from_dict,
    to_dict,
)
from regintel.models.serialization import from_json, to_json

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def make_source_location() -> SourceLocation:
    return SourceLocation(file="my_driver.sv", line=42)


def make_failure(
    occurrence_id: str = "occ0001",
    signature_id: str = "sig0001",
    test_name: str = "axi_sanity",
) -> Failure:
    return Failure(
        occurrence_id=occurrence_id,
        signature_id=signature_id,
        signature_version="v1",
        test_name=test_name,
        seed=42,
        severity=Severity.ERROR,
        raw_message="UVM_ERROR my_driver.sv(42) @ 100ns: [DRV] Bus stalled",
        normalized_message="UVM_ERROR my_driver.sv(<n>) @ <TIME>: [DRV] Bus stalled",
        location=make_source_location(),
        context_before=("line before",),
        context_after=("line after",),
        log_path=Path("logs/axi_sanity.log"),
        log_line=10,
        extractor="uvm",
        extractor_keys=("uvm_test_top.env.driver",),
        raw_fields=MappingProxyType({"uvm_tag": "DRV"}),
    )


def make_cluster(failure: Failure) -> Cluster:
    return Cluster(
        cluster_id=failure.signature_id,
        signature=failure.normalized_message,
        representative_failure_id=failure.occurrence_id,
        member_failure_ids=(failure.occurrence_id,),
        size=1,
        affected_tests=(failure.test_name,),
        common_location=failure.location,
        clustering_method="signature",
        tier=1,
        confidence=1.0,
        cross_run_annotations=MappingProxyType({}),
    )


def make_run_entry() -> TestResult:
    return TestResult(
        test_name="axi_sanity",
        seed=42,
        status=TestStatus.FAIL,
        duration_s=1.5,
        log_path=Path("logs/axi_sanity.log"),
    )


def make_run() -> Run:
    return Run(
        run_id="run0001",
        timestamp=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        project="minimal",
        simulator="verilator",
        commit_sha="abc123",
        tests=(make_run_entry(),),
        manifest_path=Path("examples/minimal/manifest.json"),
    )


def make_flaky() -> FlakyTest:
    return FlakyTest(test_name="axi_sanity", total_runs=5, failures=3, flaky_score=0.6)


def make_report() -> AnalysisReport:
    failure = make_failure()
    cluster = make_cluster(failure)
    return AnalysisReport(
        report_id="rep0001",
        generated_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        tool_version="0.1.0",
        config_snapshot=MappingProxyType({"normalization_version": "v1"}),
        runs=(make_run(),),
        failures=(failure,),
        clusters=(cluster,),
        flaky_tests=(make_flaky(),),
        stats=MappingProxyType({"total_tests": 1, "total_failures": 1}),
    )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------

def test_source_location_roundtrip() -> None:
    obj = make_source_location()
    assert from_dict(SourceLocation, to_dict(obj)) == obj


def test_source_location_none_fields_roundtrip() -> None:
    obj = SourceLocation(file=None, line=None)
    assert from_dict(SourceLocation, to_dict(obj)) == obj


def test_failure_roundtrip() -> None:
    obj = make_failure()
    assert from_dict(Failure, to_dict(obj)) == obj


def test_failure_no_seed_roundtrip() -> None:
    f = make_failure()
    fields = {field: getattr(f, field) for field in f.__dataclass_fields__}
    obj = Failure(**{**fields, "seed": None})
    assert from_dict(Failure, to_dict(obj)) == obj


def test_cluster_roundtrip() -> None:
    obj = make_cluster(make_failure())
    assert from_dict(Cluster, to_dict(obj)) == obj


def test_cluster_no_location_roundtrip() -> None:
    c = make_cluster(make_failure())
    fields = {field: getattr(c, field) for field in c.__dataclass_fields__}
    obj = Cluster(**{**fields, "common_location": None})
    assert from_dict(Cluster, to_dict(obj)) == obj


def test_run_entry_roundtrip() -> None:
    obj = make_run_entry()
    assert from_dict(TestResult, to_dict(obj)) == obj


def test_run_roundtrip() -> None:
    obj = make_run()
    assert from_dict(Run, to_dict(obj)) == obj


def test_flaky_roundtrip() -> None:
    obj = make_flaky()
    assert from_dict(FlakyTest, to_dict(obj)) == obj


def test_analysis_report_roundtrip() -> None:
    obj = make_report()
    assert from_dict(AnalysisReport, to_dict(obj)) == obj


def test_json_roundtrip() -> None:
    obj = make_report()
    assert from_json(to_json(obj)) == obj


def test_from_dict_unknown_type_raises() -> None:
    with pytest.raises(TypeError):
        from_dict(str, {})
