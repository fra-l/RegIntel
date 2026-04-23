"""End-to-end integration tests — verified after each milestone."""

import json
from pathlib import Path

import regintel
from regintel.ingestion.loader import load_run
from regintel.pipeline import analyze

MINIMAL_MANIFEST = Path(__file__).parent.parent / "fixtures/manifests/minimal.json"


def test_version_is_string() -> None:
    assert isinstance(regintel.__version__, str)
    assert regintel.__version__


# ---------------------------------------------------------------------------
# M3 — extraction pipeline
# ---------------------------------------------------------------------------

def test_load_run_returns_run_and_failures() -> None:
    run, _failures = load_run(MINIMAL_MANIFEST)
    assert run.simulator == "verilator"
    assert run.run_id


def test_load_run_extracts_failures_from_failing_tests() -> None:
    _run, failures = load_run(MINIMAL_MANIFEST)
    assert len(failures) >= 1


def test_load_run_passes_only_correct_test_names() -> None:
    _run, failures = load_run(MINIMAL_MANIFEST)
    assert "passing_test" not in {f.test_name for f in failures}


def test_load_run_failures_have_valid_signatures() -> None:
    _, failures = load_run(MINIMAL_MANIFEST)
    for f in failures:
        assert len(f.signature_id) == 16
        assert len(f.occurrence_id) == 16
        assert f.signature_version == "v1"


def test_load_run_deterministic() -> None:
    _, failures_a = load_run(MINIMAL_MANIFEST)
    _, failures_b = load_run(MINIMAL_MANIFEST)
    assert sorted(f.occurrence_id for f in failures_a) == sorted(
        f.occurrence_id for f in failures_b
    )


# ---------------------------------------------------------------------------
# M5 — full pipeline + all three output formats
# ---------------------------------------------------------------------------

def test_analyze_returns_report() -> None:
    report = analyze(MINIMAL_MANIFEST)
    assert report.tool_version == regintel.__version__
    assert report.runs
    assert report.failures
    assert report.clusters


def test_analyze_clusters_have_all_failures() -> None:
    report = analyze(MINIMAL_MANIFEST)
    clustered = {mid for c in report.clusters for mid in c.member_failure_ids}
    all_ids = {f.occurrence_id for f in report.failures}
    assert all_ids == clustered


def test_terminal_output_renders() -> None:
    import io

    from regintel.reporting.terminal import render_terminal
    report = analyze(MINIMAL_MANIFEST)
    buf = io.StringIO()
    render_terminal(report, file=buf, width=120)
    assert len(buf.getvalue()) > 0


def test_html_output_written(tmp_path: Path) -> None:
    from regintel.reporting.html import render_html
    report = analyze(MINIMAL_MANIFEST)
    out = tmp_path / "report.html"
    render_html(report, out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_json_output_valid(tmp_path: Path) -> None:
    from regintel.reporting.json_export import write_json
    report = analyze(MINIMAL_MANIFEST)
    out = tmp_path / "report.json"
    write_json(report, out)
    d = json.loads(out.read_text())
    assert d["schema_version"] == "1.0"
    assert len(d["failures"]) == len(report.failures)
    assert len(d["clusters"]) == len(report.clusters)


def test_full_pipeline_cluster_ids_deterministic() -> None:
    report_a = analyze(MINIMAL_MANIFEST)
    report_b = analyze(MINIMAL_MANIFEST)
    ids_a = sorted(c.cluster_id for c in report_a.clusters)
    ids_b = sorted(c.cluster_id for c in report_b.clusters)
    assert ids_a == ids_b
