from collections import defaultdict
from collections.abc import Mapping, Sequence

from rapidfuzz.fuzz import token_set_ratio

from regintel.clustering._helpers import merge_clusters
from regintel.clustering.base import StructuralKey
from regintel.config import ClusteringConfig
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure


def _pairwise_min_similarity(failures: Sequence[Failure]) -> float:
    if len(failures) <= 1:
        return 100.0
    min_sim = 100.0
    msgs = [f.normalized_message for f in failures]
    for i, a in enumerate(msgs):
        for b in msgs[i + 1 :]:
            sim = token_set_ratio(a, b)
            if sim < min_sim:
                min_sim = sim
    return min_sim


def tier2_structural(
    clusters: list[Cluster],
    failures_by_id: Mapping[str, Failure],
    config: ClusteringConfig,
) -> list[Cluster]:
    groups: dict[StructuralKey, list[Cluster]] = defaultdict(list)
    for c in clusters:
        rep = failures_by_id[c.representative_failure_id]
        key = StructuralKey(
            severity=rep.severity,
            file=rep.location.file,
            line=rep.location.line,
            extractor=rep.extractor,
            extractor_keys=rep.extractor_keys,
        )
        groups[key].append(c)

    merged: list[Cluster] = []
    for _key, group in sorted(groups.items(), key=lambda kv: kv[1][0].cluster_id):
        if len(group) == 1:
            merged.append(group[0])
            continue

        reps = [failures_by_id[c.representative_failure_id] for c in group]
        if _pairwise_min_similarity(reps) >= config.tier2_min_similarity:
            merged.append(merge_clusters(group, failures_by_id, "structural", 2, 0.9))
        else:
            merged.extend(group)

    return merged
