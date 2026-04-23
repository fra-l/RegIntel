"""Tests for assemble_blocks and context_lines."""

from regintel.extractors.base import FailureBlock, assemble_blocks, context_lines
from regintel.extractors.generic import GenericExtractor

_EXT = GenericExtractor()


def _blocks(lines: list[str]) -> list[FailureBlock]:
    return list(assemble_blocks(_EXT, lines))


def test_no_primaries_yields_no_blocks() -> None:
    assert _blocks(["info line", "another line"]) == []


def test_single_primary_yields_one_block() -> None:
    blocks = _blocks(["Error: something went wrong"])
    assert len(blocks) == 1
    assert blocks[0].primary_line == "Error: something went wrong"
    assert blocks[0].continuation_lines == ()


def test_primary_line_number_is_correct() -> None:
    blocks = _blocks(["prefix", "Error: bad thing", "suffix"])
    assert blocks[0].primary_line_no == 1


def test_generic_has_no_continuations() -> None:
    blocks = _blocks(["Error: bad", "  detail line", "Error: another"])
    # generic extractor never has continuations
    assert len(blocks) == 2
    assert blocks[0].continuation_lines == ()


def test_empty_log_yields_no_blocks() -> None:
    assert _blocks([]) == []


def test_context_lines_middle() -> None:
    lines = [f"line{i}" for i in range(20)]
    before, after = context_lines(lines, primary_line_no=10, n=3)
    assert before == ("line7", "line8", "line9")
    assert after == ("line11", "line12", "line13")


def test_context_lines_near_start() -> None:
    lines = ["a", "b", "c", "d", "e"]
    before, after = context_lines(lines, primary_line_no=1, n=5)
    assert before == ("a",)  # only 1 line before
    assert "b" not in after  # primary excluded


def test_context_lines_near_end() -> None:
    lines = ["a", "b", "c"]
    _before, after = context_lines(lines, primary_line_no=2, n=5)
    assert after == ()
