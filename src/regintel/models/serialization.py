"""
Serialization helpers for RegIntel models.

Public API:
  to_dict(obj)          recursive dict conversion (JSON-compatible)
  from_dict(cls, d)     reconstruct any model from dict via dispatcher
  to_json(report)       AnalysisReport → JSON string
  from_json(s)          JSON string → AnalysisReport
"""

import dataclasses
import json
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from regintel.models.cluster import Cluster
from regintel.models.failure import Failure, Severity, SourceLocation
from regintel.models.report import AnalysisReport, FlakyTest
from regintel.models.run import Run, TestResult, TestStatus

# ---------------------------------------------------------------------------
# to_dict — generic recursive serializer
# ---------------------------------------------------------------------------

def to_dict(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, MappingProxyType):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(i) for i in obj]
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    return obj


# ---------------------------------------------------------------------------
# Per-class from_dict reconstructors (private — use from_dict() publicly)
# ---------------------------------------------------------------------------

def _source_location_from_dict(d: dict[str, Any]) -> SourceLocation:
    return SourceLocation(file=d.get("file"), line=d.get("line"))


def _failure_from_dict(d: dict[str, Any]) -> Failure:
    return Failure(
        occurrence_id=d["occurrence_id"],
        signature_id=d["signature_id"],
        signature_version=d["signature_version"],
        test_name=d["test_name"],
        seed=d.get("seed"),
        severity=Severity(d["severity"]),
        raw_message=d["raw_message"],
        normalized_message=d["normalized_message"],
        location=_source_location_from_dict(d["location"]),
        context_before=tuple(d["context_before"]),
        context_after=tuple(d["context_after"]),
        log_path=Path(d["log_path"]),
        log_line=d["log_line"],
        extractor=d["extractor"],
        extractor_keys=tuple(d["extractor_keys"]),
        raw_fields=MappingProxyType(d.get("raw_fields") or {}),
    )


def _cluster_from_dict(d: dict[str, Any]) -> Cluster:
    loc = d.get("common_location")
    return Cluster(
        cluster_id=d["cluster_id"],
        signature=d["signature"],
        representative_failure_id=d["representative_failure_id"],
        member_failure_ids=tuple(d["member_failure_ids"]),
        size=d["size"],
        affected_tests=tuple(d["affected_tests"]),
        common_location=_source_location_from_dict(loc) if loc is not None else None,
        clustering_method=d["clustering_method"],
        tier=d["tier"],
        confidence=d["confidence"],
        cross_run_annotations=MappingProxyType(d.get("cross_run_annotations") or {}),
    )


def _run_entry_from_dict(d: dict[str, Any]) -> TestResult:
    return TestResult(
        test_name=d["test_name"],
        seed=d.get("seed"),
        status=TestStatus(d["status"]),
        duration_s=d.get("duration_s"),
        log_path=Path(d["log_path"]),
    )


def _run_from_dict(d: dict[str, Any]) -> Run:
    return Run(
        run_id=d["run_id"],
        timestamp=datetime.fromisoformat(d["timestamp"]),
        project=d.get("project"),
        simulator=d["simulator"],
        commit_sha=d.get("commit_sha"),
        tests=tuple(_run_entry_from_dict(t) for t in d["tests"]),
        manifest_path=Path(d["manifest_path"]),
    )


def _flaky_from_dict(d: dict[str, Any]) -> FlakyTest:
    return FlakyTest(
        test_name=d["test_name"],
        total_runs=d["total_runs"],
        failures=d["failures"],
        flaky_score=d["flaky_score"],
    )


def _report_from_dict(d: dict[str, Any]) -> AnalysisReport:
    return AnalysisReport(
        report_id=d["report_id"],
        generated_at=datetime.fromisoformat(d["generated_at"]),
        tool_version=d["tool_version"],
        config_snapshot=MappingProxyType(d.get("config_snapshot") or {}),
        runs=tuple(_run_from_dict(r) for r in d["runs"]),
        failures=tuple(_failure_from_dict(f) for f in d["failures"]),
        clusters=tuple(_cluster_from_dict(c) for c in d["clusters"]),
        flaky_tests=tuple(_flaky_from_dict(ft) for ft in d["flaky_tests"]),
        stats=MappingProxyType(d.get("stats") or {}),
    )


# ---------------------------------------------------------------------------
# JSON convenience layer
# ---------------------------------------------------------------------------

def to_json(report: AnalysisReport, indent: int = 2) -> str:
    return json.dumps({"schema_version": "1.0", **to_dict(report)}, indent=indent)


def from_json(s: str) -> AnalysisReport:
    d = json.loads(s)
    d.pop("schema_version", None)
    return _report_from_dict(d)


# ---------------------------------------------------------------------------
# Generic from_dict dispatcher — public API for tests and consumers
# ---------------------------------------------------------------------------

_RECONSTRUCTORS: Mapping[type[Any], Any] = {
    Failure: _failure_from_dict,
    Cluster: _cluster_from_dict,
    TestResult: _run_entry_from_dict,
    Run: _run_from_dict,
    FlakyTest: _flaky_from_dict,
    AnalysisReport: _report_from_dict,
    SourceLocation: _source_location_from_dict,
}


def from_dict(cls: type[Any], d: dict[str, Any]) -> Any:
    reconstructor = _RECONSTRUCTORS.get(cls)
    if reconstructor is None:
        raise TypeError(f"No from_dict reconstructor registered for {cls}")
    return reconstructor(d)
