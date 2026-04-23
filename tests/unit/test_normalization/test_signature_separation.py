"""Separation tests: distinct bugs must produce different signatures."""

import json
from itertools import combinations
from pathlib import Path

import pytest

from regintel.models.failure import Severity
from regintel.normalization.rules import normalize
from regintel.normalization.signature import compute_signature

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "signature_separation"


def _load_groups() -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    return [(f.stem, json.loads(f.read_text())) for f in sorted(FIXTURE_DIR.glob("*.json"))]


def _sig_for_variant(v: dict, group: dict) -> str:  # type: ignore[type-arg]
    msg = v.get("message", group.get("message", ""))
    severity = Severity(v.get("severity", group.get("severity", "error")))
    file: str | None = v.get("file", group.get("file"))
    line: int | None = v.get("line", group.get("line"))
    extractor_keys = tuple(v.get("extractor_keys", group.get("extractor_keys", [])))
    return compute_signature(
        normalized_message=normalize(msg),
        file=file,
        line=line,
        severity=severity,
        extractor_keys=extractor_keys,
    )


@pytest.mark.parametrize("name,group", _load_groups())
def test_separation_group(name: str, group: dict) -> None:  # type: ignore[type-arg]
    """All variants in a separation group must produce pairwise different signatures."""
    variants = group["variants"]
    signatures = [_sig_for_variant(v, group) for v in variants]

    for (i, sig_a), (j, sig_b) in combinations(enumerate(signatures), 2):
        assert sig_a != sig_b, (
            f"Separation group '{name}': variants {i} and {j} produced the same signature "
            f"({sig_a!r}) — they should be different bugs."
        )
