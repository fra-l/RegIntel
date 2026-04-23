"""Shared helpers used by multiple clustering tiers."""

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from regintel.models.cluster import Cluster
from regintel.models.failure import Failure, SourceLocation
from regintel.utils.hashing import stable_hash

_SEP = "\x1f"


def common_location(failures: Sequence[Failure]) -> SourceLocation | None:
    files = {f.location.file for f in failures}
    lines = {f.location.line for f in failures}
    if len(files) == 1 and len(lines) == 1:
        return SourceLocation(file=next(iter(files)), line=next(iter(lines)))
    return None


def merge_clusters(
    clusters: Sequence[Cluster],
    failures_by_id: Mapping[str, Failure],
    method: str,
    tier: int,
    confidence: float,
) -> Cluster:
    all_member_ids = tuple(
        sorted(mid for c in clusters for mid in c.member_failure_ids)
    )
    merged_id = stable_hash(_SEP.join(all_member_ids))
    rep_id = all_member_ids[0]  # lex-smallest occurrence_id

    affected = tuple(sorted({failures_by_id[mid].test_name for mid in all_member_ids}))
    all_failures = [failures_by_id[mid] for mid in all_member_ids]

    return Cluster(
        cluster_id=merged_id,
        signature=failures_by_id[rep_id].normalized_message,
        representative_failure_id=rep_id,
        member_failure_ids=all_member_ids,
        size=len(all_member_ids),
        affected_tests=affected,
        common_location=common_location(all_failures),
        clustering_method=method,
        tier=tier,
        confidence=confidence,
        cross_run_annotations=MappingProxyType({}),
    )
