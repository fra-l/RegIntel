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

# Primary line must start with UVM_WARNING / UVM_ERROR / UVM_FATAL.
# UVM_INFO is not a failure and is intentionally excluded.
_PRIMARY_RE = re.compile(r"^UVM_(WARNING|ERROR|FATAL)\b")

# UVM message anatomy (all parts optional except severity):
#   UVM_ERROR [file.sv(line)] @ time: component.path [TAG] message text
_FILE_LINE_RE = re.compile(r"(\S+\.(?:sv|svh|v|verilog|vhd))\((\d+)\)")
_AFTER_COLON_RE = re.compile(r":\s*([\w.]+(?:\[\w*\])*)\s+\[([^\]]+)\]")
# Normalise array indices in component paths: foo[0].bar → foo[N].bar
_ARRAY_INDEX_RE = re.compile(r"\[\d+\]")

_SEVERITY_MAP: dict[str, Severity] = {
    "UVM_WARNING": Severity.WARNING,
    "UVM_ERROR": Severity.ERROR,
    "UVM_FATAL": Severity.FATAL,
}


def _extract_severity(primary_line: str) -> Severity:
    m = _PRIMARY_RE.match(primary_line)
    if m:
        return _SEVERITY_MAP.get(f"UVM_{m.group(1)}", Severity.UNKNOWN)
    return Severity.UNKNOWN


def _extract_location(primary_line: str) -> SourceLocation:
    m = _FILE_LINE_RE.search(primary_line)
    if m:
        return SourceLocation(file=m.group(1), line=int(m.group(2)))
    return SourceLocation(file=None, line=None)


def _extract_component_info(primary_line: str) -> tuple[str | None, str | None]:
    """Return (component_path, tag) from a UVM primary line, or (None, None)."""
    m = _AFTER_COLON_RE.search(primary_line)
    if m:
        path = _ARRAY_INDEX_RE.sub("[N]", m.group(1))
        return path, m.group(2)
    return None, None


class UVMExtractor:
    name = "uvm"
    priority = 10

    def can_handle(self, test: TestResult, log_head: str) -> bool:
        return "UVM_" in log_head

    def is_primary(self, line: str) -> bool:
        return bool(_PRIMARY_RE.match(line))

    def is_continuation(self, line: str, block_so_far: Sequence[str]) -> bool:
        if not line.strip():
            return False
        if _PRIMARY_RE.match(line):
            return False
        # Accept indented lines (UVM continuation details are always indented)
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
        component_path, tag = _extract_component_info(block.primary_line)

        # Both component path and tag contribute to the signature so that
        # two different scoreboard instances reporting the same queue name
        # get different signatures (the SyoSil two-scoreboards requirement).
        keys: list[str] = []
        if component_path:
            keys.append(component_path)
        if tag:
            keys.append(tag)
        extractor_keys = tuple(sorted(keys))

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
            raw_fields=MappingProxyType(
                {"uvm_component_path": component_path, "uvm_tag": tag}
            ),
        )


register(UVMExtractor())
