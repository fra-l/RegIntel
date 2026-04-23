"""Stability tests: variants of the same bug must produce the same signature."""

import json
from pathlib import Path

import pytest

from regintel.models.failure import Severity
from regintel.normalization.rules import normalize
from regintel.normalization.signature import compute_signature

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "signature_stability"


def _load_groups() -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    return [(f.stem, json.loads(f.read_text())) for f in sorted(FIXTURE_DIR.glob("*.json"))]


@pytest.mark.parametrize("name,group", _load_groups())
def test_stability_group(name: str, group: dict) -> None:  # type: ignore[type-arg]
    """All variants in a stability group must produce the same signature."""
    severity = Severity(group["severity"])
    file: str | None = group.get("file")
    line: int | None = group.get("line")
    extractor_keys = tuple(group.get("extractor_keys", []))

    variants = group["variants"]
    # Variants may be plain strings or dicts with per-variant overrides.
    signatures = set()
    for v in variants:
        is_str = isinstance(v, str)
        msg = v if is_str else v["message"]
        v_sev = severity if is_str else Severity(v.get("severity", severity.value))
        v_keys = extractor_keys if is_str else tuple(v.get("extractor_keys", list(extractor_keys)))
        sig = compute_signature(
            normalized_message=normalize(msg),
            file=file if is_str else v.get("file", file),
            line=line if is_str else v.get("line", line),
            severity=v_sev,
            extractor_keys=v_keys,
        )
        signatures.add(sig)

    assert len(signatures) == 1, (
        f"Stability group '{name}' produced {len(signatures)} different signatures — "
        f"expected 1. Signatures: {signatures}"
    )
