"""Shared factories for clustering tests."""

from pathlib import Path
from types import MappingProxyType
from typing import Any

from regintel.models.failure import Failure, Severity, SourceLocation
from regintel.normalization.rules import normalize
from regintel.normalization.signature import SIGNATURE_VERSION, compute_signature
from regintel.utils.hashing import compute_occurrence_id

_LOG_PATH = Path("logs/test.log")
_RUN_ID = "test-run-000"


def make_failure(
    *,
    test_name: str = "test_a",
    seed: int | None = None,
    severity: Severity = Severity.ERROR,
    message: str = "UVM_ERROR Bus stalled",
    file: str | None = "drv.sv",
    line: int | None = 42,
    extractor: str = "uvm",
    extractor_keys: tuple[str, ...] = ("uvm_test_top.env.driver", "DRV"),
    log_line: int = 0,
    raw_fields: dict[str, Any] | None = None,
) -> Failure:
    normalized = normalize(message)
    sig_id = compute_signature(normalized, file, line, severity, extractor_keys)
    occ_id = compute_occurrence_id(
        run_id=_RUN_ID,
        test_name=test_name,
        seed=seed,
        log_path=_LOG_PATH,
        log_line=log_line,
        raw_message=message,
    )
    return Failure(
        occurrence_id=occ_id,
        signature_id=sig_id,
        signature_version=SIGNATURE_VERSION,
        test_name=test_name,
        seed=seed,
        severity=severity,
        raw_message=message,
        normalized_message=normalized,
        location=SourceLocation(file=file, line=line),
        context_before=(),
        context_after=(),
        log_path=_LOG_PATH,
        log_line=log_line,
        extractor=extractor,
        extractor_keys=extractor_keys,
        raw_fields=MappingProxyType(raw_fields or {}),
    )
