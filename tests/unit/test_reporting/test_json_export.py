"""Schema and round-trip tests for the JSON export."""

import json

from regintel.models.report import AnalysisReport
from regintel.reporting.json_export import to_json

_EXPECTED_KEYS = {
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


def test_json_export_top_level_keys(minimal_report: AnalysisReport) -> None:
    d = json.loads(to_json(minimal_report))
    assert set(d.keys()) == _EXPECTED_KEYS


def test_json_export_schema_version(minimal_report: AnalysisReport) -> None:
    d = json.loads(to_json(minimal_report))
    assert d["schema_version"] == "1.0"


def test_json_export_failure_count(minimal_report: AnalysisReport) -> None:
    d = json.loads(to_json(minimal_report))
    assert len(d["failures"]) == 3


def test_json_export_cluster_count(minimal_report: AnalysisReport) -> None:
    d = json.loads(to_json(minimal_report))
    assert len(d["clusters"]) == 2


def test_json_export_is_pretty(minimal_report: AnalysisReport) -> None:
    output = to_json(minimal_report)
    assert "\n" in output  # pretty-printed


def test_json_export_deterministic(minimal_report: AnalysisReport) -> None:
    assert to_json(minimal_report) == to_json(minimal_report)
