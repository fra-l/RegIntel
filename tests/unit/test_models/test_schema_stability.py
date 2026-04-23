"""Schema stability test — catches accidental field additions or removals."""

import json
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

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
)
from regintel.models.serialization import to_json


def _make_report() -> AnalysisReport:
    failure = Failure(
        occurrence_id="occ0001",
        signature_id="sig0001",
        signature_version="v1",
        test_name="axi_sanity",
        seed=42,
        severity=Severity.ERROR,
        raw_message="UVM_ERROR my_driver.sv(42) @ 100ns: Bus stalled",
        normalized_message="UVM_ERROR my_driver.sv(<n>) @ <TIME>: Bus stalled",
        location=SourceLocation(file="my_driver.sv", line=42),
        context_before=(),
        context_after=(),
        log_path=Path("logs/axi_sanity.log"),
        log_line=10,
        extractor="uvm",
        extractor_keys=("uvm_test_top.env.driver",),
        raw_fields=MappingProxyType({}),
    )
    cluster = Cluster(
        cluster_id="sig0001",
        signature="UVM_ERROR my_driver.sv(<n>) @ <TIME>: Bus stalled",
        representative_failure_id="occ0001",
        member_failure_ids=("occ0001",),
        size=1,
        affected_tests=("axi_sanity",),
        common_location=SourceLocation(file="my_driver.sv", line=42),
        clustering_method="signature",
        tier=1,
        confidence=1.0,
        cross_run_annotations=MappingProxyType({}),
    )
    test_result = TestResult(
        test_name="axi_sanity",
        seed=42,
        status=TestStatus.FAIL,
        duration_s=1.5,
        log_path=Path("logs/axi_sanity.log"),
    )
    run = Run(
        run_id="run0001",
        timestamp=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        project="minimal",
        simulator="verilator",
        commit_sha=None,
        tests=(test_result,),
        manifest_path=Path("manifest.json"),
    )
    return AnalysisReport(
        report_id="rep0001",
        generated_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        tool_version="0.1.0",
        config_snapshot=MappingProxyType({}),
        runs=(run,),
        failures=(failure,),
        clusters=(cluster,),
        flaky_tests=(FlakyTest("axi_sanity", 3, 2, 0.667),),
        stats=MappingProxyType({"total_failures": 1}),
    )


# Expected top-level keys for AnalysisReport JSON — update when schema changes.
_EXPECTED_REPORT_KEYS = {
    "schema_version",
    "report_id",
    "generated_at",
    "tool_version",
    "config_snapshot",
    "runs",
    "failures",
    "clusters",
    "flaky_tests",
    "stats",
}

_EXPECTED_FAILURE_KEYS = {
    "occurrence_id",
    "signature_id",
    "signature_version",
    "test_name",
    "seed",
    "severity",
    "raw_message",
    "normalized_message",
    "location",
    "context_before",
    "context_after",
    "log_path",
    "log_line",
    "extractor",
    "extractor_keys",
    "raw_fields",
}

_EXPECTED_CLUSTER_KEYS = {
    "cluster_id",
    "signature",
    "representative_failure_id",
    "member_failure_ids",
    "size",
    "affected_tests",
    "common_location",
    "clustering_method",
    "tier",
    "confidence",
    "cross_run_annotations",
}


def test_report_top_level_keys() -> None:
    report = _make_report()
    d = json.loads(to_json(report))
    assert set(d.keys()) == _EXPECTED_REPORT_KEYS


def test_failure_keys() -> None:
    report = _make_report()
    d = json.loads(to_json(report))
    failure_dict = d["failures"][0]
    assert set(failure_dict.keys()) == _EXPECTED_FAILURE_KEYS


def test_cluster_keys() -> None:
    report = _make_report()
    d = json.loads(to_json(report))
    cluster_dict = d["clusters"][0]
    assert set(cluster_dict.keys()) == _EXPECTED_CLUSTER_KEYS


def test_schema_version_present() -> None:
    report = _make_report()
    d = json.loads(to_json(report))
    assert d["schema_version"] == "1.0"


def test_json_roundtrip() -> None:
    from regintel.models.serialization import from_json
    report = _make_report()
    assert from_json(to_json(report)) == report
