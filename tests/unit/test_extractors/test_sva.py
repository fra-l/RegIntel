"""Tests for the SVA assertion extractor."""

from pathlib import Path

from regintel.extractors.base import assemble_blocks
from regintel.extractors.sva import SVAExtractor
from regintel.models.failure import Failure, Severity
from regintel.models.run import TestResult, TestStatus

FIXTURE = Path(__file__).parent.parent.parent / "fixtures/logs/verilator/sva_assertion/test.log"
_RUN_ID = "test-run-000"
_EXT = SVAExtractor()


def _make_test(path: Path = FIXTURE) -> TestResult:
    return TestResult(
        test_name="sva_test", seed=None, status=TestStatus.FAIL, duration_s=None, log_path=path
    )


def _extract(path: Path = FIXTURE) -> list[Failure]:
    lines = path.read_text().splitlines()
    test = _make_test(path)
    return [_EXT.build_failure(b, test, _RUN_ID, lines) for b in assemble_blocks(_EXT, lines)]


def test_can_handle_sva_log() -> None:
    head = FIXTURE.read_text()[:500]
    assert _EXT.can_handle(_make_test(), head)


def test_can_handle_rejects_uvm_log() -> None:
    head = "UVM_ERROR @ 100ns: path [TAG] msg\nAssertion failed for property foo"
    assert not _EXT.can_handle(_make_test(), head)


def test_is_primary_matches_assertion_failed() -> None:
    assert _EXT.is_primary('"sva_checkers.sv", line 27: Assertion failed for property prop_a')


def test_is_primary_rejects_normal_lines() -> None:
    assert not _EXT.is_primary("Simulation starting...")
    assert not _EXT.is_primary("UVM_ERROR @ 100ns: path [TAG]")


def test_fixture_extracts_two_failures() -> None:
    failures = _extract()
    assert len(failures) == 2


def test_severity_is_error() -> None:
    failures = _extract()
    assert all(f.severity == Severity.ERROR for f in failures)


def test_extractor_name() -> None:
    failures = _extract()
    assert all(f.extractor == "sva" for f in failures)


def test_location_extracted() -> None:
    failures = _extract()
    f = failures[0]
    assert f.location.file == "sva_checkers.sv"
    assert f.location.line == 27


def test_property_name_in_extractor_keys() -> None:
    failures = _extract()
    f = failures[0]
    assert "prop_grant_valid" in f.extractor_keys


def test_different_properties_different_signatures() -> None:
    failures = _extract()
    assert failures[0].signature_id != failures[1].signature_id
