"""Tests for the generic (fallback) extractor."""

from pathlib import Path

from regintel.extractors.base import assemble_blocks
from regintel.extractors.generic import GenericExtractor
from regintel.models.failure import Failure, Severity
from regintel.models.run import TestResult, TestStatus

FIXTURE = Path(__file__).parent.parent.parent / "fixtures/logs/verilator/generic_error/test.log"
_RUN_ID = "test-run-000"
_EXT = GenericExtractor()


def _make_test() -> TestResult:
    return TestResult(
        test_name="generic_test",
        seed=None,
        status=TestStatus.FAIL,
        duration_s=None,
        log_path=FIXTURE,
    )


def _extract_failures(log_path: Path) -> list[Failure]:
    lines = log_path.read_text().splitlines()
    test = TestResult(
        test_name="t", seed=None, status=TestStatus.FAIL, duration_s=None, log_path=log_path
    )
    return [_EXT.build_failure(b, test, _RUN_ID, lines) for b in assemble_blocks(_EXT, lines)]


def test_can_handle_always_true() -> None:
    assert _EXT.can_handle(_make_test(), "") is True


def test_is_continuation_always_false() -> None:
    assert _EXT.is_continuation("  indented detail", []) is False


def test_primary_matches_error_colon() -> None:
    assert _EXT.is_primary("Error: something bad")
    assert _EXT.is_primary("error: lowercase")
    assert _EXT.is_primary("Fatal: catastrophic")


def test_primary_matches_failed() -> None:
    assert _EXT.is_primary("Simulation FAILED")


def test_primary_rejects_info() -> None:
    assert not _EXT.is_primary("INFO: all good")
    assert not _EXT.is_primary("just a log line")


def test_fixture_extracts_expected_count() -> None:
    failures = _extract_failures(FIXTURE)
    # generic_error/test.log has: "Fatal:", "Error:", "FAILED" — 3 matches
    assert len(failures) == 3


def test_fixture_severity_inference() -> None:
    failures = _extract_failures(FIXTURE)
    sevs = {f.severity for f in failures}
    assert Severity.FATAL in sevs
    assert Severity.ERROR in sevs


def test_extractor_name() -> None:
    failures = _extract_failures(FIXTURE)
    assert all(f.extractor == "generic" for f in failures)


def test_no_extractor_keys() -> None:
    failures = _extract_failures(FIXTURE)
    assert all(f.extractor_keys == () for f in failures)


def test_malformed_garbage_produces_no_failures() -> None:
    garbage = Path(__file__).parent.parent.parent / "fixtures/logs/verilator/malformed/garbage.log"
    failures = _extract_failures(garbage)
    assert failures == []


def test_malformed_truncated_does_not_crash() -> None:
    truncated = (
        Path(__file__).parent.parent.parent / "fixtures/logs/verilator/malformed/truncated.log"
    )
    failures = _extract_failures(truncated)
    assert isinstance(failures, list)
