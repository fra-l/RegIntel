"""Snapshot and behaviour tests for the terminal reporter."""

import io
import re

from regintel.models.report import AnalysisReport
from regintel.reporting.terminal import exit_code, render_terminal


def _capture(report: AnalysisReport, **kwargs: object) -> str:
    buf = io.StringIO()
    render_terminal(report, file=buf, width=120, **kwargs)  # type: ignore[arg-type]
    raw = buf.getvalue()
    # Strip ANSI escape codes
    return re.sub(r"\x1b\[[0-9;]*m", "", raw)


def test_headline_contains_failure_count(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report)
    assert "3" in out  # total_failures
    assert "2" in out  # total_clusters


def test_headline_contains_analysis_time(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report)
    assert "0.42s" in out


def test_cluster_count_shown(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report)
    assert "Cluster 1" in out
    assert "Cluster 2" in out


def test_top_limits_output(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report, top=1)
    assert "Cluster 1" in out
    assert "Cluster 2" not in out


def test_verbose_shows_member_tests(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report, verbose=True)
    assert "axi_sanity" in out


def test_no_flaky_section_when_empty(minimal_report: AnalysisReport) -> None:
    out = _capture(minimal_report)
    assert "Flaky" not in out


def test_exit_code_any_with_clusters(minimal_report: AnalysisReport) -> None:
    assert exit_code(minimal_report, "any") == 1


def test_exit_code_none_always_zero(minimal_report: AnalysisReport) -> None:
    assert exit_code(minimal_report, "none") == 0


def test_exit_code_any_no_clusters(minimal_report: AnalysisReport) -> None:
    import dataclasses
    empty = dataclasses.replace(minimal_report, clusters=())
    assert exit_code(empty, "any") == 0
