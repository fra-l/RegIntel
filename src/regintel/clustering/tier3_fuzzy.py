from collections import defaultdict
from collections.abc import Mapping

from rapidfuzz.fuzz import token_set_ratio

from regintel.clustering._helpers import merge_clusters
from regintel.config import ClusteringConfig
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure

_SKIP_TOKENS = frozenset(
    {
        "<HEX>", "<NUM>", "<TIME>", "<ADDR>", "<n>", "<N>",
        "ERROR:", "FATAL:", "WARNING:",
        "UVM_ERROR", "UVM_FATAL", "UVM_WARNING",
        "%Error:", "%Warning:",
        "@",
    }
)


def _first_significant_token(normalized_message: str) -> str:
    for token in normalized_message.split():
        if token not in _SKIP_TOKENS and not token.startswith("<"):
            return token
    return ""


def _scale_fuzzy_confidence(similarity: float, threshold: float) -> float:
    span = 100.0 - threshold
    if span <= 0:
        return 0.85
    fraction = (similarity - threshold) / span
    return round(min(0.85, 0.6 + fraction * 0.25), 3)


def _violates_never_merge(
    a: Cluster,
    b: Cluster,
    failures_by_id: Mapping[str, Failure],
) -> bool:
    fa = failures_by_id[a.representative_failure_id]
    fb = failures_by_id[b.representative_failure_id]

    if fa.severity != fb.severity:
        return True
    if fa.extractor != fb.extractor:
        return True
    if fa.location.file and fb.location.file and fa.location.file != fb.location.file:
        return True
    return bool(
        fa.extractor_keys and fb.extractor_keys and fa.extractor_keys != fb.extractor_keys
    )


def _merge_within_block(
    candidates: list[Cluster],
    failures_by_id: Mapping[str, Failure],
    config: ClusteringConfig,
) -> list[Cluster]:
    # Greedy representative-based merging (no chaining).
    # Each candidate is compared only to the representative of an existing group.
    groups: list[list[Cluster]] = []

    for candidate in sorted(candidates, key=lambda c: c.cluster_id):
        joined = False
        for group in groups:
            group_rep_msg = failures_by_id[group[0].representative_failure_id].normalized_message
            cand_msg = failures_by_id[candidate.representative_failure_id].normalized_message
            similarity = token_set_ratio(cand_msg, group_rep_msg)
            if similarity >= config.tier3_threshold and not _violates_never_merge(
                candidate, group[0], failures_by_id
            ):
                group.append(candidate)
                joined = True
                break
        if not joined:
            groups.append([candidate])

    out: list[Cluster] = []
    for group in groups:
        if len(group) == 1:
            out.append(group[0])
            continue

        rep_msg = failures_by_id[group[0].representative_failure_id].normalized_message
        similarities = [
            token_set_ratio(
                rep_msg,
                failures_by_id[c.representative_failure_id].normalized_message,
            )
            for c in group[1:]
        ]
        min_sim = min(similarities)
        conf = _scale_fuzzy_confidence(min_sim, config.tier3_threshold)
        out.append(merge_clusters(group, failures_by_id, "fuzzy", 3, conf))

    return out


def tier3_fuzzy(
    clusters: list[Cluster],
    failures_by_id: Mapping[str, Failure],
    config: ClusteringConfig,
) -> list[Cluster]:
    small = [c for c in clusters if c.size < config.tier3_max_cluster_size]
    large = [c for c in clusters if c.size >= config.tier3_max_cluster_size]

    def _block_key(c: Cluster) -> tuple[str, str, str]:
        rep = failures_by_id[c.representative_failure_id]
        return (
            rep.severity.value,
            rep.extractor,
            _first_significant_token(rep.normalized_message),
        )

    blocks: dict[tuple[str, str, str], list[Cluster]] = defaultdict(list)
    for c in sorted(small, key=lambda c: c.cluster_id):
        blocks[_block_key(c)].append(c)

    result: list[Cluster] = list(large)
    for block_clusters in blocks.values():
        result.extend(_merge_within_block(block_clusters, failures_by_id, config))

    return result
