"""Shared AnalysisReport fixture for reporter tests."""

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from regintel.models import (
    AnalysisReport,
    Cluster,
    Failure,
    Run,
    Severity,
    SourceLocation,
    TestResult,
    TestStatus,
)
from regintel.normalization.rules import normalize
from regintel.normalization.signature import SIGNATURE_VERSION, compute_signature
from regintel.utils.hashing import compute_occurrence_id

_RUN_ID = "report-test-run"
_LOG = Path("logs/test.log")
_MANIFEST = Path("tests/fixtures/manifests/minimal.json")


def _make_failure(
    msg: str,
    test: str = "axi_sanity",
    log_line: int = 0,
    extractor_keys: tuple[str, ...] = ("uvm_test_top.env.driver", "DRV"),
) -> Failure:
    norm = normalize(msg)
    loc = SourceLocation(file="drv.sv", line=42)
    sig = compute_signature(norm, loc.file, loc.line, Severity.ERROR, extractor_keys)
    occ = compute_occurrence_id(_RUN_ID, test, None, _LOG, log_line, msg)
    return Failure(
        occurrence_id=occ,
        signature_id=sig,
        signature_version=SIGNATURE_VERSION,
        test_name=test,
        seed=None,
        severity=Severity.ERROR,
        raw_message=msg,
        normalized_message=norm,
        location=loc,
        context_before=("prev line",),
        context_after=("next line",),
        log_path=_LOG,
        log_line=log_line,
        extractor="uvm",
        extractor_keys=extractor_keys,
        raw_fields=MappingProxyType({}),
    )


@pytest.fixture
def minimal_report() -> AnalysisReport:
    f1 = _make_failure("UVM_ERROR @ 100ns: uvm_test_top.env.driver [DRV] Bus stalled", log_line=0)
    f2 = _make_failure("UVM_ERROR @ 200ns: uvm_test_top.env.driver [DRV] Bus stalled", log_line=1)
    f3 = _make_failure(
        "UVM_ERROR @ 300ns: uvm_test_top.env.mem_sb [SCB] MISMATCH in queue payload_q",
        log_line=2,
        extractor_keys=("uvm_test_top.env.mem_sb", "SCB"),
    )

    cluster1 = Cluster(
        cluster_id=f1.signature_id,
        signature=f1.normalized_message,
        representative_failure_id=min(f1.occurrence_id, f2.occurrence_id),
        member_failure_ids=tuple(sorted([f1.occurrence_id, f2.occurrence_id])),
        size=2,
        affected_tests=("axi_sanity",),
        common_location=f1.location,
        clustering_method="signature",
        tier=1,
        confidence=1.0,
        cross_run_annotations=MappingProxyType({}),
    )
    cluster2 = Cluster(
        cluster_id=f3.signature_id,
        signature=f3.normalized_message,
        representative_failure_id=f3.occurrence_id,
        member_failure_ids=(f3.occurrence_id,),
        size=1,
        affected_tests=("axi_sanity",),
        common_location=f3.location,
        clustering_method="signature",
        tier=1,
        confidence=1.0,
        cross_run_annotations=MappingProxyType({}),
    )

    run = Run(
        run_id=_RUN_ID,
        timestamp=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        project="test",
        simulator="verilator",
        commit_sha=None,
        tests=(
            TestResult(
                test_name="axi_sanity",
                seed=None,
                status=TestStatus.FAIL,
                duration_s=1.5,
                log_path=_LOG,
            ),
        ),
        manifest_path=_MANIFEST,
    )

    return AnalysisReport(
        report_id="test-report-0001",
        generated_at=datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC),
        tool_version="0.1.0",
        config_snapshot=MappingProxyType({"normalization_version": "v1"}),
        runs=(run,),
        failures=(f1, f2, f3),
        clusters=(cluster1, cluster2),
        flaky_tests=(),
        stats=MappingProxyType({
            "total_tests": 1,
            "total_failures": 3,
            "total_clusters": 2,
            "tier1_clusters": 2,
            "tier2_merges": 0,
            "tier3_merges": 0,
            "analysis_duration_s": 0.42,
            "extractor_usage": {"uvm": 3},
        }),
    )
