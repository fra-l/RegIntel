from dataclasses import dataclass

from regintel.models.cluster import Cluster
from regintel.models.report import AnalysisReport

_TRUNCATE_LEN = 100
_TEST_SUMMARY_MAX = 3


@dataclass(frozen=True)
class FailureView:
    occurrence_id: str
    test_name: str
    seed: int | None
    log_path: str
    log_line: int
    context_before: tuple[str, ...]
    primary_line: str
    context_after: tuple[str, ...]


@dataclass(frozen=True)
class ClusterView:
    cluster_id: str
    rank: int
    tier: int
    clustering_method: str
    confidence: float
    confidence_band: str  # "high" | "medium" | "low"
    size: int
    truncated_rep: str
    full_rep: str
    location_display: str
    extractor_keys: tuple[str, ...]
    test_summary: str
    affected_tests: tuple[str, ...]
    member_failures: tuple[FailureView, ...]


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.9:
        return "high"
    if confidence >= 0.7:
        return "medium"
    return "low"


def _truncate(s: str, n: int = _TRUNCATE_LEN) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _test_summary(tests: tuple[str, ...]) -> str:
    if len(tests) <= _TEST_SUMMARY_MAX:
        return ", ".join(tests)
    shown = ", ".join(tests[:_TEST_SUMMARY_MAX])
    return f"{shown} (+{len(tests) - _TEST_SUMMARY_MAX})"


def build_cluster_view(cluster: Cluster, report: AnalysisReport, rank: int) -> ClusterView:
    rep_failure = report.failure_by_id[cluster.representative_failure_id]

    member_failures = tuple(
        FailureView(
            occurrence_id=f.occurrence_id,
            test_name=f.test_name,
            seed=f.seed,
            log_path=str(f.log_path),
            log_line=f.log_line,
            context_before=f.context_before,
            primary_line=f.raw_message.splitlines()[0],
            context_after=f.context_after,
        )
        for mid in cluster.member_failure_ids
        for f in [report.failure_by_id[mid]]
    )

    loc = cluster.common_location
    location_display = str(loc) if loc and loc.file else "<unknown>"

    return ClusterView(
        cluster_id=cluster.cluster_id,
        rank=rank,
        tier=cluster.tier,
        clustering_method=cluster.clustering_method,
        confidence=cluster.confidence,
        confidence_band=_confidence_band(cluster.confidence),
        size=cluster.size,
        truncated_rep=_truncate(rep_failure.normalized_message),
        full_rep=rep_failure.normalized_message,
        location_display=location_display,
        extractor_keys=cluster.extractor_keys if hasattr(cluster, "extractor_keys")
            else rep_failure.extractor_keys,
        test_summary=_test_summary(cluster.affected_tests),
        affected_tests=cluster.affected_tests,
        member_failures=member_failures,
    )


def build_all_cluster_views(report: AnalysisReport) -> list[ClusterView]:
    return [
        build_cluster_view(c, report, rank=i + 1)
        for i, c in enumerate(report.clusters)
    ]
