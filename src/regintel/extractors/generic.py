import re
from collections.abc import Sequence
from types import MappingProxyType

from regintel.extractors.base import FailureBlock, context_lines
from regintel.extractors.registry import register
from regintel.models.failure import Failure, Severity, SourceLocation
from regintel.models.run import TestResult
from regintel.normalization.rules import normalize
from regintel.normalization.signature import SIGNATURE_VERSION, compute_signature
from regintel.utils.hashing import compute_occurrence_id

_PRIMARY_RE = re.compile(r"\bError:|\bFatal:|\berror:|\bFATAL:|\bFAILED\b")

_SEVERITY_HINTS = [
    (re.compile(r"\bFatal:", re.IGNORECASE), Severity.FATAL),
    (re.compile(r"\bError:", re.IGNORECASE), Severity.ERROR),
]


def _infer_severity(line: str) -> Severity:
    for pattern, sev in _SEVERITY_HINTS:
        if pattern.search(line):
            return sev
    return Severity.UNKNOWN


class GenericExtractor:
    name = "generic"
    priority = 100

    def can_handle(self, test: TestResult, log_head: str) -> bool:
        return True

    def is_primary(self, line: str) -> bool:
        return bool(_PRIMARY_RE.search(line))

    def is_continuation(self, line: str, block_so_far: Sequence[str]) -> bool:
        return False

    def build_failure(
        self,
        block: FailureBlock,
        test: TestResult,
        run_id: str,
        log_lines: Sequence[str],
    ) -> Failure:
        raw_message = block.primary_line
        severity = _infer_severity(raw_message)
        normalized = normalize(raw_message)
        ctx_before, ctx_after = context_lines(log_lines, block.primary_line_no)

        sig_id = compute_signature(
            normalized_message=normalized,
            file=None,
            line=None,
            severity=severity,
            extractor_keys=(),
        )
        occ_id = compute_occurrence_id(
            run_id=run_id,
            test_name=test.test_name,
            seed=test.seed,
            log_path=test.log_path,
            log_line=block.primary_line_no,
            raw_message=raw_message,
        )

        return Failure(
            occurrence_id=occ_id,
            signature_id=sig_id,
            signature_version=SIGNATURE_VERSION,
            test_name=test.test_name,
            seed=test.seed,
            severity=severity,
            raw_message=raw_message,
            normalized_message=normalized,
            location=SourceLocation(file=None, line=None),
            context_before=ctx_before,
            context_after=ctx_after,
            log_path=test.log_path,
            log_line=block.primary_line_no,
            extractor=self.name,
            extractor_keys=(),
            raw_fields=MappingProxyType({}),
        )


register(GenericExtractor())
