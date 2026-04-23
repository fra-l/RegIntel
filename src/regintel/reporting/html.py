"""HTML reporter — single self-contained file output."""

from __future__ import annotations

from pathlib import Path

import jinja2

from regintel.models.report import AnalysisReport
from regintel.reporting.view_model import build_all_cluster_views

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=jinja2.select_autoescape(["html"]),
)


def render_html(report: AnalysisReport, output_path: Path) -> None:
    template = _env.get_template("report.html.j2")
    views = build_all_cluster_views(report)
    stats = report.stats

    html = template.render(
        report=report,
        cluster_views=views,
        stats=stats,
        tool_version=report.tool_version,
        generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        manifest_path=str(report.runs[0].manifest_path) if report.runs else "",
    )
    output_path.write_text(html, encoding="utf-8")
