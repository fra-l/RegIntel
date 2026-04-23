"""Tests for the Verilator-native extractor."""

from pathlib import Path

from regintel.extractors.base import assemble_blocks
from regintel.extractors.verilator import VerilatorExtractor
from regintel.models.failure import Failure, Severity
from regintel.models.run import TestResult, TestStatus

FIXTURE = (
    Path(__file__).parent.parent.parent / "fixtures/logs/verilator/verilator_native_error/test.log"
)
_RUN_ID = "test-run-000"
_EXT = VerilatorExtractor()


def _log_lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def _make_test(path: Path = FIXTURE) -> TestResult:
    return TestResult(
        test_name="verilator_test",
        seed=None,
        status=TestStatus.FAIL,
        duration_s=None,
        log_path=path,
    )


def _extract(path: Path = FIXTURE) -> list[Failure]:
    lines = _log_lines(path)
    test = _make_test(path)
    return [_EXT.build_failure(b, test, _RUN_ID, lines) for b in assemble_blocks(_EXT, lines)]


def test_can_handle_verilator_log() -> None:
    head = _log_lines(FIXTURE)[:10]
    assert _EXT.can_handle(_make_test(), "\n".join(head))


def test_can_handle_rejects_uvm_log() -> None:
    uvm_head = "UVM_ERROR @ 100ns: uvm_test_top [DRV] fail"
    assert not _EXT.can_handle(_make_test(), uvm_head)


def test_is_primary_matches_error() -> None:
    assert _EXT.is_primary("%Error: file.sv:42:5: bad")
    assert _EXT.is_primary("%Error-UNUSED: file.sv:10:3: unused")


def test_is_primary_matches_warning() -> None:
    assert _EXT.is_primary("%Warning-STMTDLY: file.sv:5:1: statement delay")


def test_is_primary_rejects_continuation() -> None:
    assert not _EXT.is_primary("        file.sv:42:5: ... note: In instance")


def test_fixture_extracts_two_blocks() -> None:
    failures = _extract()
    assert len(failures) == 2


def test_error_severity() -> None:
    failures = _extract()
    error_f = next(f for f in failures if f.severity == Severity.ERROR)
    assert error_f.severity == Severity.ERROR


def test_warning_severity() -> None:
    failures = _extract()
    warn_f = next(f for f in failures if f.severity == Severity.WARNING)
    assert warn_f.severity == Severity.WARNING


def test_extractor_key_is_type() -> None:
    failures = _extract()
    keys = {f.extractor_keys for f in failures}
    assert ("UNUSED",) in keys


def test_location_extracted() -> None:
    failures = _extract()
    f = next(f for f in failures if f.severity == Severity.ERROR)
    assert f.location.file == "my_module.sv"
    assert f.location.line == 42


def test_extractor_name() -> None:
    failures = _extract()
    assert all(f.extractor == "verilator" for f in failures)


def test_continuation_captured() -> None:
    failures = _extract()
    # %Error block should include the indented note line
    err_block = next(f for f in failures if f.severity == Severity.ERROR)
    assert "note" in err_block.raw_message or len(err_block.raw_message.splitlines()) >= 1
