"""Property-based tests for normalization using Hypothesis."""

from hypothesis import given, settings
from hypothesis import strategies as st

from regintel.models.failure import Severity
from regintel.normalization.rules import normalize
from regintel.normalization.signature import compute_signature

# Restrict to printable ASCII to keep tests focused on normalizer logic.
_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=200)


@given(_text)
def test_normalize_is_idempotent(s: str) -> None:
    assert normalize(normalize(s)) == normalize(s)


@given(_text)
def test_normalize_extra_internal_whitespace_irrelevant(s: str) -> None:
    # Adding a space between characters produces the same normalized output.
    s2 = s.replace(" ", "  ")
    assert normalize(s) == normalize(s2)


@given(_text)
def test_normalize_leading_trailing_whitespace_irrelevant(s: str) -> None:
    assert normalize(s) == normalize(f"  {s}  ")


@given(_text)
def test_normalize_output_has_no_raw_long_integers(s: str) -> None:
    # After normalization, no standalone 4+ digit integers should remain.
    import re
    result = normalize(s)
    raw_longs = re.findall(r"\b\d{4,}\b", result)
    assert raw_longs == [], f"Raw long integers left in output: {raw_longs!r}"


@given(
    _text,
    st.none() | st.text(min_size=1, max_size=50),
    st.none() | st.integers(min_value=1, max_value=10000),
    st.sampled_from(list(Severity)),
    st.lists(st.text(min_size=1, max_size=30), max_size=5),
)
def test_signature_is_deterministic(
    msg: str,
    file: str | None,
    line: int | None,
    severity: Severity,
    keys: list[str],
) -> None:
    normalized = normalize(msg)
    extractor_keys = tuple(keys)
    sig_a = compute_signature(normalized, file, line, severity, extractor_keys)
    sig_b = compute_signature(normalized, file, line, severity, extractor_keys)
    assert sig_a == sig_b


@given(
    _text,
    st.none() | st.text(min_size=1, max_size=50),
    st.none() | st.integers(min_value=1, max_value=10000),
    st.sampled_from(list(Severity)),
    st.lists(st.text(min_size=1, max_size=30), max_size=5),
)
def test_signature_key_order_irrelevant(
    msg: str,
    file: str | None,
    line: int | None,
    severity: Severity,
    keys: list[str],
) -> None:
    # extractor_keys are sorted inside compute_signature — order must not matter.
    normalized = normalize(msg)
    sig_a = compute_signature(normalized, file, line, severity, tuple(keys))
    sig_b = compute_signature(normalized, file, line, severity, tuple(reversed(keys)))
    assert sig_a == sig_b


@given(_text)
@settings(max_examples=50)
def test_normalize_output_is_single_line(s: str) -> None:
    result = normalize(s)
    assert "\n" not in result
