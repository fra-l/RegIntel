from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from regintel.models.failure import Failure
from regintel.models.run import TestResult

_CONTEXT_LINES = 5


@dataclass(frozen=True)
class FailureBlock:
    primary_line: str
    primary_line_no: int
    continuation_lines: tuple[str, ...]
    continuation_line_nos: tuple[int, ...]


class Extractor(Protocol):
    name: str
    priority: int

    def can_handle(self, test: TestResult, log_head: str) -> bool: ...

    def is_primary(self, line: str) -> bool: ...

    def is_continuation(self, line: str, block_so_far: Sequence[str]) -> bool: ...

    def build_failure(
        self,
        block: FailureBlock,
        test: TestResult,
        run_id: str,
        log_lines: Sequence[str],
    ) -> Failure: ...


def assemble_blocks(
    extractor: Extractor,
    log_lines: Sequence[str],
) -> Iterator[FailureBlock]:
    i = 0
    while i < len(log_lines):
        line = log_lines[i]
        if not extractor.is_primary(line):
            i += 1
            continue

        continuation_lines: list[str] = []
        continuation_line_nos: list[int] = []
        j = i + 1
        while j < len(log_lines):
            if extractor.is_primary(log_lines[j]):
                break
            if not extractor.is_continuation(log_lines[j], continuation_lines):
                break
            continuation_lines.append(log_lines[j])
            continuation_line_nos.append(j)
            j += 1

        yield FailureBlock(
            primary_line=line,
            primary_line_no=i,
            continuation_lines=tuple(continuation_lines),
            continuation_line_nos=tuple(continuation_line_nos),
        )
        i = j


def context_lines(
    log_lines: Sequence[str],
    primary_line_no: int,
    n: int = _CONTEXT_LINES,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    before = tuple(log_lines[max(0, primary_line_no - n) : primary_line_no])
    after = tuple(log_lines[primary_line_no + 1 : primary_line_no + 1 + n])
    return before, after
