import hashlib
from pathlib import Path

_SEP = "\x1f"  # unit separator; never appears in normal log text


def compute_occurrence_id(
    run_id: str,
    test_name: str,
    seed: int | None,
    log_path: Path,
    log_line: int,
    raw_message: str,
) -> str:
    parts = (
        run_id,
        test_name,
        str(seed) if seed is not None else "",
        str(log_path),
        str(log_line),
        raw_message,
    )
    return _sha1(_SEP.join(parts))


def stable_hash(payload: str) -> str:
    return _sha1(payload)


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
