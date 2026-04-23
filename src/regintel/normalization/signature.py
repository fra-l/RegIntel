import hashlib

from regintel.models.failure import Severity

SIGNATURE_VERSION = "v1"

_SEP = "\x1f"


def compute_signature(
    normalized_message: str,
    file: str | None,
    line: int | None,
    severity: Severity,
    extractor_keys: tuple[str, ...] = (),
) -> str:
    sorted_keys = tuple(sorted(extractor_keys))
    parts = (
        SIGNATURE_VERSION,
        severity.value,
        file or "",
        str(line) if line is not None else "",
        normalized_message,
        *sorted_keys,
    )
    payload = _SEP.join(parts).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:16]
