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

# %Error: file.sv:42:5: message
# %Error-TYPE: file.sv:42:5: message
# %Warning-TYPE: ...
_PRIMARY_RE = re.compile(r"^%(?:Error|Warning)(?:-\w+)?:")
_TYPE_RE = re.compile(r"^%(?:Error|Warning)-(\w+):")
_LOCATION_RE = re.compile(r":\s*(\S+\.(?:sv|svh|v|verilog|vhd))\s*:\s*(\d+)")


def _extract_type(primary_line: str) -> str | None:
    m = _TYPE_RE.match(primary_line)
    return m.group(1) if m else None


def _extract_location(primary_line: str) -> SourceLocation:
    m = _LOCATION_RE.search(primary_line)
    if m:
        return SourceLocation(file=m.group(1), line=int(m.group(2)))
    return SourceLocation(file=None, line=None)


def _extract_severity(primary_line: str) -> Severity:
    if primary_line.startswith("%Error"):
        return Severity.ERROR
    return Severity.WARNING


class VerilatorExtractor:
    name = "verilator"
    priority = 30

    def can_handle(self, test: TestResult, log_head: str) -> bool:
        return bool(_PRIMARY_RE.search(log_head))

    def is_primary(self, line: str) -> bool:
        return bool(_PRIMARY_RE.match(line))

    def is_continuation(self, line: str, block_so_far: Sequence[str]) -> bool:
        if not line.strip():
            return False
        if _PRIMARY_RE.match(line):
            return False
        # Verilator continuation lines are indented context/fix hints
        return line[:1] in (" ", "\t")

    def build_failure(
        self,
        block: FailureBlock,
        test: TestResult,
        run_id: str,
        log_lines: Sequence[str],
    ) -> Failure:
        raw_message = block.primary_line
        if block.continuation_lines:
            raw_message += "\n" + "\n".join(block.continuation_lines)

        severity = _extract_severity(block.primary_line)
        location = _extract_location(block.primary_line)
        msg_type = _extract_type(block.primary_line)
        extractor_keys = (msg_type,) if msg_type else ()

        normalized = normalize(block.primary_line)
        ctx_before, ctx_after = context_lines(log_lines, block.primary_line_no)

        sig_id = compute_signature(
            normalized_message=normalized,
            file=location.file,
            line=location.line,
            severity=severity,
            extractor_keys=extractor_keys,
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
            location=location,
            context_before=ctx_before,
            context_after=ctx_after,
            log_path=test.log_path,
            log_line=block.primary_line_no,
            extractor=self.name,
            extractor_keys=extractor_keys,
            raw_fields=MappingProxyType({"verilator_type": msg_type}),
        )


register(VerilatorExtractor())
