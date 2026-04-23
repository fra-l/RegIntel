from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from regintel.models.failure import SourceLocation


@dataclass(frozen=True)
class Cluster:
    cluster_id: str
    signature: str
    representative_failure_id: str
    member_failure_ids: tuple[str, ...]
    size: int
    affected_tests: tuple[str, ...]
    common_location: SourceLocation | None
    clustering_method: str
    tier: int
    confidence: float
    cross_run_annotations: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.cross_run_annotations, MappingProxyType):
            object.__setattr__(
                self,
                "cross_run_annotations",
                MappingProxyType(dict(self.cross_run_annotations)),
            )
