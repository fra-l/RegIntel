from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from regintel.models.cluster import Cluster
from regintel.models.failure import Failure, Severity


class Clusterer(Protocol):
    name: str
    tier: int

    def cluster(
        self,
        input_clusters: list[Cluster],
        failures_by_id: Mapping[str, Failure],
    ) -> list[Cluster]: ...


@dataclass(frozen=True)
class StructuralKey:
    severity: Severity
    file: str | None
    line: int | None
    extractor: str
    extractor_keys: tuple[str, ...]
