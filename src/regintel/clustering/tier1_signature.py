from collections import defaultdict
from collections.abc import Sequence
from types import MappingProxyType

from regintel.clustering._helpers import common_location
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure


def tier1_signature_exact(failures: Sequence[Failure]) -> list[Cluster]:
    groups: dict[str, list[Failure]] = defaultdict(list)
    for f in sorted(failures, key=lambda f: f.occurrence_id):
        groups[f.signature_id].append(f)

    clusters: list[Cluster] = []
    for sig_id, members in groups.items():
        rep = members[0]  # lex-first by occurrence_id (already sorted)
        clusters.append(
            Cluster(
                cluster_id=sig_id,
                signature=rep.normalized_message,
                representative_failure_id=rep.occurrence_id,
                member_failure_ids=tuple(m.occurrence_id for m in members),
                size=len(members),
                affected_tests=tuple(sorted({m.test_name for m in members})),
                common_location=common_location(members),
                clustering_method="signature",
                tier=1,
                confidence=1.0,
                cross_run_annotations=MappingProxyType({}),
            )
        )

    return sorted(clusters, key=lambda c: (-c.size, c.cluster_id))
