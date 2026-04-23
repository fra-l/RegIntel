from __future__ import annotations

import sys
from pathlib import Path

import click

from regintel.config import ClusteringConfig, Config


@click.group()
def main() -> None:
    pass


@main.command()
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@click.option("--html", "html_path", type=click.Path(path_type=Path), default=None,
              help="Write HTML report to PATH (default: regintel-report.html).")
@click.option("--json", "json_path", type=click.Path(path_type=Path), default=None,
              help="Write JSON export to PATH.")
@click.option("--terminal-only", is_flag=True, default=False,
              help="Skip file outputs; print terminal summary only.")
@click.option("--top", default=10, show_default=True,
              help="Number of clusters shown in terminal summary.")
@click.option("--verbose", is_flag=True, default=False,
              help="Show all clusters and member details.")
@click.option("--fail-on",
              type=click.Choice(["new", "any", "none"]),
              default="any", show_default=True,
              help="Exit non-zero when: any clusters / new clusters only / never.")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path),
              default=None, help="Load settings from a TOML file.")
def analyze(
    manifest: Path,
    html_path: Path | None,
    json_path: Path | None,
    terminal_only: bool,
    top: int,
    verbose: bool,
    fail_on: str,
    config_path: Path | None,
) -> None:
    """Analyze a Verilator regression run from MANIFEST."""
    from regintel.pipeline import analyze as _analyze
    from regintel.reporting.html import render_html
    from regintel.reporting.json_export import write_json
    from regintel.reporting.terminal import exit_code, render_terminal

    config = _load_config(config_path)

    try:
        report = _analyze(manifest, config)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    # Terminal output is always produced.
    render_terminal(report, top=top, verbose=verbose)

    if not terminal_only:
        dest = html_path or Path("regintel-report.html")
        render_html(report, dest)
        click.echo(f"\nHTML report: {dest}", err=True)

    if json_path:
        write_json(report, json_path)
        click.echo(f"JSON export: {json_path}", err=True)

    sys.exit(exit_code(report, fail_on))


def _load_config(config_path: Path | None) -> Config:
    if config_path is None:
        return Config()
    import tomllib

    with open(config_path, "rb") as fh:
        raw = tomllib.load(fh)

    cc_raw = raw.get("clustering", {})
    cc = ClusteringConfig(
        enable_tier2=cc_raw.get("enable_tier2", True),
        enable_tier3=cc_raw.get("enable_tier3", True),
        tier2_min_similarity=cc_raw.get("tier2_min_similarity", 60),
        tier3_threshold=cc_raw.get("tier3_threshold", 85),
        tier3_max_cluster_size=cc_raw.get("tier3_max_cluster_size", 5),
        fuzzy_algorithm=cc_raw.get("fuzzy_algorithm", "token_set_ratio"),
    )
    return Config(clustering=cc)
