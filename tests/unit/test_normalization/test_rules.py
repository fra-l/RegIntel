"""Golden fixture tests for the normalization rule engine."""

from pathlib import Path

import pytest

from regintel.normalization.rules import normalize

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "normalization"


def _fixture_pairs() -> list[tuple[str, str]]:
    inputs = sorted(FIXTURE_DIR.glob("*.input.txt"))
    pairs = []
    for inp in inputs:
        expected = inp.with_suffix("").with_suffix(".expected.txt")
        assert expected.exists(), f"Missing expected file for {inp.name}"
        pairs.append((inp.stem.replace(".input", ""), str(inp)))
    return pairs


@pytest.mark.parametrize("name,input_path", _fixture_pairs())
def test_normalization_fixture(name: str, input_path: str) -> None:
    inp = Path(input_path)
    expected_path = inp.with_suffix("").with_suffix(".expected.txt")
    raw = inp.read_text(encoding="utf-8")
    expected = expected_path.read_text(encoding="utf-8").strip()
    assert normalize(raw) == expected, f"Fixture '{name}' failed"


# ---------------------------------------------------------------------------
# Targeted unit tests for specific rule behavior
# ---------------------------------------------------------------------------

def test_empty_string() -> None:
    assert normalize("") == ""


def test_only_whitespace() -> None:
    assert normalize("   ") == ""


def test_multiline_takes_first_line() -> None:
    assert normalize("first line\nsecond line") == normalize("first line")


def test_hex_before_decimal() -> None:
    # 0xABCD must not become 0x<NUM> (i.e., hex rule must fire first)
    result = normalize("value is 0xABCDEF")
    assert result == "value is <HEX>"
    assert "<NUM>" not in result


def test_time_before_decimal() -> None:
    result = normalize("delay is 1234ns")
    assert result == "delay is <TIME>"
    assert "<NUM>" not in result


def test_array_index_before_integer() -> None:
    result = normalize("mem[1024] overflow")
    assert result == "mem[<N>] overflow"
    assert "<NUM>" not in result


def test_absolute_path_stripped_to_basename() -> None:
    result = normalize("error in /home/user/tb/my_driver.sv")
    assert "my_driver.sv" in result
    assert "/home/" not in result


def test_relative_path_unchanged() -> None:
    result = normalize("error in tb/my_driver.sv")
    assert "tb/my_driver.sv" in result


def test_seed_kv_normalized() -> None:
    assert "seed=<N>" in normalize("failed with seed=12345")


def test_pid_kv_normalized() -> None:
    assert "pid=<N>" in normalize("process pid=9876 crashed")


def test_host_kv_normalized() -> None:
    assert "host=<HOST>" in normalize("running on host=ci-runner-07")


def test_four_digit_integer_becomes_num() -> None:
    result = normalize("counter at 5000")
    assert "<NUM>" in result
    assert "5000" not in result


def test_small_integer_becomes_n() -> None:
    result = normalize("line 42 failed")
    assert "<n>" in result
    assert "42" not in result


def test_whitespace_collapsed() -> None:
    assert normalize("a  b   c") == "a b c"


def test_semantic_keywords_preserved() -> None:
    msg = "MISMATCH TIMEOUT OVERFLOW EXPECTED GOT ASSERTION"
    result = normalize(msg)
    for kw in ["MISMATCH", "TIMEOUT", "OVERFLOW", "EXPECTED", "GOT", "ASSERTION"]:
        assert kw in result
