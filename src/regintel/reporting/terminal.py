"""Terminal reporter using Rich."""

from __future__ import annotations

import sys
from typing import IO

from rich.box import ROUNDED, SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from regintel.models.report import AnalysisReport
from regintel.reporting.view_model import ClusterView, build_all_cluster_views

_CONFIDENCE_STYLE: dict[str, str] = {
    "high": "bold green",
    "medium": "yellow",
    "low": "bold orange1",
}

_SEVERITY_STYLE: dict[str, str] = {
    "fatal": "bold red",
    "error": "orange1",
    "warning": "yellow",
    "unknown": "dim",
}


def _headline(report: AnalysisReport) -> Panel:
    stats = report.stats
    dur = stats.get("analysis_duration_s", 0)
    text = (
        f"[bold]{stats.get('total_tests', 0)}[/] tests  ·  "
        f"[bold]{stats.get('total_failures', 0)}[/] failures  ·  "
        f"[bold]{stats.get('total_clusters', 0)}[/] clusters  ·  "
        f"analyzed in [bold]{dur}s[/]"
    )
    return Panel(text, title="[bold]RegIntel Analysis[/]", box=ROUNDED, expand=False)


def _cluster_panel(cv: ClusterView, verbose: bool) -> Panel:
    lines: list[str] = []

    # Representative message
    prefix = "[[bold cyan]FUZZY[/]] " if cv.tier == 3 else ""
    lines.append(f"{prefix}{cv.truncated_rep}")

    # Location
    if cv.location_display != "<unknown>":
        lines.append(f"[dim]at[/] {cv.location_display}")

    # Extractor keys (scoreboard instance, property name, etc.)
    if cv.extractor_keys:
        keys_str = " · ".join(cv.extractor_keys)
        lines.append(f"[dim]keys:[/] {keys_str}")

    # Test summary
    lines.append(f"[dim]affects[/] {cv.test_summary}")

    if verbose:
        lines.append("")
        for fv in cv.member_failures:
            seed_str = f"  seed={fv.seed}" if fv.seed is not None else ""
            lines.append(f"  [dim]·[/] {fv.test_name}{seed_str}  {fv.log_path}:{fv.log_line}")

    conf_style = _CONFIDENCE_STYLE[cv.confidence_band]
    conf_str = f"[{conf_style}]confidence {cv.confidence:.2f}[/]"
    title = (
        f"[bold]Cluster {cv.rank}[/]  ·  "
        f"[bold]{cv.size}[/] failure{'s' if cv.size != 1 else ''}  ·  "
        f"{conf_str}"
    )

    return Panel("\n".join(lines), title=title, box=SIMPLE, expand=True)


def _flaky_table(report: AnalysisReport) -> Table | None:
    if not report.flaky_tests:
        return None
    table = Table(title="Flaky Tests", box=SIMPLE, show_header=True, header_style="bold")
    table.add_column("Test", style="cyan")
    table.add_column("Failures", justify="right")
    table.add_column("Runs", justify="right")
    table.add_column("Score", justify="right")
    for ft in report.flaky_tests:
        table.add_row(
            ft.test_name,
            str(ft.failures),
            str(ft.total_runs),
            f"{ft.flaky_score:.0%}",
        )
    return table


def render_terminal(
    report: AnalysisReport,
    top: int = 10,
    verbose: bool = False,
    file: IO[str] | None = None,
    width: int = 120,
) -> None:
    console = Console(file=file or sys.stdout, width=width, highlight=False)
    views = build_all_cluster_views(report)

    console.print()
    console.print(_headline(report))
    console.print()

    display = views if verbose else views[:top]
    if display:
        n_shown = len(display)
        n_total = len(views)
        suffix = f" (showing {n_shown} of {n_total})" if n_total > n_shown else ""
        console.print(f"[bold]Top clusters ({n_total}){suffix}:[/]")
        console.print()
        for cv in display:
            console.print(_cluster_panel(cv, verbose))

    flaky = _flaky_table(report)
    if flaky:
        console.print()
        console.print(flaky)

    if not verbose and views:
        console.print()
        console.print(
            "[dim]Run with [bold]--verbose[/bold] for full details, "
            "or open the HTML report for the complete analysis.[/]"
        )


def exit_code(report: AnalysisReport, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    if fail_on in {"any", "new"} and report.clusters:
        return 1
    return 0
