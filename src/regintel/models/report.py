from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from regintel.models.cluster import Cluster
from regintel.models.failure import Failure
from regintel.models.run import Run


@dataclass(frozen=True)
class FlakyTest:
    test_name: str
    total_runs: int
    failures: int
    flaky_score: float


@dataclass(frozen=True)
class AnalysisReport:
    # identity and provenance
    report_id: str
    generated_at: datetime
    tool_version: str
    config_snapshot: Mapping[str, Any]

    # content
    runs: tuple[Run, ...]
    failures: tuple[Failure, ...]
    clusters: tuple[Cluster, ...]
    flaky_tests: tuple[FlakyTest, ...]

    # summary stats
    stats: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.config_snapshot, MappingProxyType):
            object.__setattr__(
                self, "config_snapshot", MappingProxyType(dict(self.config_snapshot))
            )
        if not isinstance(self.stats, MappingProxyType):
            object.__setattr__(self, "stats", MappingProxyType(dict(self.stats)))

    @property
    def failure_by_id(self) -> Mapping[str, Failure]:
        return MappingProxyType({f.occurrence_id: f for f in self.failures})

    @property
    def cluster_by_id(self) -> Mapping[str, Cluster]:
        return MappingProxyType({c.cluster_id: c for c in self.clusters})
