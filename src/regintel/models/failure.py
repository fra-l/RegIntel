from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any


class Severity(StrEnum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceLocation:
    file: str | None
    line: int | None

    def __str__(self) -> str:
        if self.file and self.line is not None:
            return f"{self.file}:{self.line}"
        if self.file:
            return self.file
        return "<unknown>"


@dataclass(frozen=True)
class Failure:
    # identity
    occurrence_id: str
    signature_id: str
    signature_version: str

    # content
    test_name: str
    seed: int | None
    severity: Severity
    raw_message: str
    normalized_message: str
    location: SourceLocation
    context_before: tuple[str, ...]
    context_after: tuple[str, ...]

    # provenance
    log_path: Path
    log_line: int
    extractor: str
    extractor_keys: tuple[str, ...]

    # escape hatch for extractor-specific extras
    raw_fields: Mapping[str, Any]

    @property
    def has_location(self) -> bool:
        return self.location.file is not None

    def __post_init__(self) -> None:
        # Ensure raw_fields is an immutable mapping
        if not isinstance(self.raw_fields, MappingProxyType):
            object.__setattr__(self, "raw_fields", MappingProxyType(dict(self.raw_fields)))
