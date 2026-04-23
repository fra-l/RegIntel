"""Tests for the UVM extractor — including the SyoSil two-scoreboards regression."""

from pathlib import Path

from regintel.extractors.base import assemble_blocks
from regintel.extractors.uvm import UVMExtractor
from regintel.models.failure import Failure, Severity
from regintel.models.run import TestResult, TestStatus

FIXTURES = Path(__file__).parent.parent.parent / "fixtures/logs/verilator"
_RUN_ID = "test-run-000"
_EXT = UVMExtractor()


def _make_test(path: Path) -> TestResult:
    return TestResult(
        test_name="uvm_test", seed=None, status=TestStatus.FAIL, duration_s=None, log_path=path
    )


def _extract(log_path: Path) -> list[Failure]:
    lines = log_path.read_text().splitlines()
    test = _make_test(log_path)
    return [_EXT.build_failure(b, test, _RUN_ID, lines) for b in assemble_blocks(_EXT, lines)]


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------

def test_can_handle_uvm_log() -> None:
    assert _EXT.can_handle(_make_test(FIXTURES / "simple_uvm_error/test.log"), "UVM_INFO ...")


def test_can_handle_rejects_non_uvm() -> None:
    assert not _EXT.can_handle(_make_test(FIXTURES / "simple_uvm_error/test.log"), "%Error: ...")


def test_is_primary_matches_error() -> None:
    assert _EXT.is_primary("UVM_ERROR @ 100ns: path [TAG] msg")


def test_is_primary_matches_fatal() -> None:
    assert _EXT.is_primary("UVM_FATAL @ 100ns: path [TAG] msg")


def test_is_primary_matches_warning() -> None:
    assert _EXT.is_primary("UVM_WARNING @ 100ns: path [TAG] msg")


def test_is_primary_rejects_info() -> None:
    assert not _EXT.is_primary("UVM_INFO @ 100ns: starting")


def test_is_continuation_accepts_indented() -> None:
    assert _EXT.is_continuation("  Expected: 0xDEAD", [])


def test_is_continuation_rejects_blank() -> None:
    assert not _EXT.is_continuation("", [])
    assert not _EXT.is_continuation("   ", [])


def test_is_continuation_rejects_new_primary() -> None:
    assert not _EXT.is_continuation("UVM_ERROR @ 200ns: other [TAG] msg", [])


# ---------------------------------------------------------------------------
# Simple UVM error fixture
# ---------------------------------------------------------------------------

def test_simple_uvm_error_extracts_one_failure() -> None:
    failures = _extract(FIXTURES / "simple_uvm_error/test.log")
    assert len(failures) == 1


def test_simple_uvm_error_severity() -> None:
    failures = _extract(FIXTURES / "simple_uvm_error/test.log")
    assert failures[0].severity == Severity.ERROR


def test_simple_uvm_error_extractor_name() -> None:
    failures = _extract(FIXTURES / "simple_uvm_error/test.log")
    assert failures[0].extractor == "uvm"


def test_simple_uvm_error_has_extractor_keys() -> None:
    failures = _extract(FIXTURES / "simple_uvm_error/test.log")
    assert len(failures[0].extractor_keys) > 0


# ---------------------------------------------------------------------------
# Multi-line block assembly
# ---------------------------------------------------------------------------

def test_multi_line_captures_continuations() -> None:
    failures = _extract(FIXTURES / "multi_line_uvm_error/test.log")
    assert len(failures) == 1
    f = failures[0]
    assert "\n" in f.raw_message
    assert "Arbiter state" in f.raw_message


def test_multi_line_location_extracted() -> None:
    failures = _extract(FIXTURES / "multi_line_uvm_error/test.log")
    f = failures[0]
    assert f.location.file == "my_driver.sv"
    assert f.location.line == 42


# ---------------------------------------------------------------------------
# Adjacent errors — block boundary test
# ---------------------------------------------------------------------------

def test_adjacent_errors_produce_two_failures() -> None:
    failures = _extract(FIXTURES / "adjacent_uvm_errors/test.log")
    assert len(failures) == 2


def test_adjacent_errors_have_different_messages() -> None:
    failures = _extract(FIXTURES / "adjacent_uvm_errors/test.log")
    assert failures[0].normalized_message != failures[1].normalized_message


# ---------------------------------------------------------------------------
# SyoSil two-scoreboards regression — THE critical test
# ---------------------------------------------------------------------------

def test_syosil_two_scoreboards_extracts_two_failures() -> None:
    failures = _extract(FIXTURES / "syosil_two_scoreboards/test.log")
    assert len(failures) == 2


def test_syosil_two_scoreboards_different_signatures() -> None:
    """axi_sb and mem_sb must produce DIFFERENT signatures despite same queue name."""
    failures = _extract(FIXTURES / "syosil_two_scoreboards/test.log")
    sig_a = failures[0].signature_id
    sig_b = failures[1].signature_id
    assert sig_a != sig_b, (
        "SyoSil regression: both scoreboards collapsed to the same signature. "
        "extractor_keys must include the component path."
    )


def test_syosil_extractor_keys_contain_scoreboard_path() -> None:
    failures = _extract(FIXTURES / "syosil_two_scoreboards/test.log")
    paths = {f.extractor_keys for f in failures}
    # Each failure must have a distinct set of extractor_keys
    assert len(paths) == 2


def test_syosil_both_failures_are_errors() -> None:
    failures = _extract(FIXTURES / "syosil_two_scoreboards/test.log")
    assert all(f.severity == Severity.ERROR for f in failures)
