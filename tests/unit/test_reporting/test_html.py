"""Smoke tests for the HTML reporter."""

import html.parser
from pathlib import Path

from regintel.models.report import AnalysisReport
from regintel.reporting.html import render_html


class _TagCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.text_chunks.append(stripped)


def _render_to_string(report: AnalysisReport, tmp_path: Path) -> str:
    out = tmp_path / "report.html"
    render_html(report, out)
    return out.read_text(encoding="utf-8")


def test_html_renders_without_error(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    assert html_str.startswith("<!DOCTYPE html>")


def test_html_is_parseable(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    collector = _TagCollector()
    collector.feed(html_str)
    assert "html" in collector.tags
    assert "head" in collector.tags
    assert "body" in collector.tags


def test_html_contains_failure_count(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    # The headline shows "3 failures → 2 clusters"
    assert "3" in html_str
    assert "2" in html_str


def test_html_contains_tool_version(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    assert "0.1.0" in html_str


def test_html_contains_cluster_cards(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    assert "cluster-card" in html_str
    assert "#1" in html_str
    assert "#2" in html_str


def test_html_contains_js_search(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    assert "getElementById('search')" in html_str or 'getElementById("search")' in html_str


def test_html_no_external_resources(minimal_report: AnalysisReport, tmp_path: Path) -> None:
    html_str = _render_to_string(minimal_report, tmp_path)
    # Self-contained: no CDN links
    assert "cdn.jsdelivr" not in html_str
    assert "unpkg.com" not in html_str
    assert '<link rel="stylesheet"' not in html_str
    assert "<script src=" not in html_str
