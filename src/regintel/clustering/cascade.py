from collections.abc import Sequence

from regintel.clustering.tier1_signature import tier1_signature_exact
from regintel.clustering.tier2_structural import tier2_structural
from regintel.clustering.tier3_fuzzy import tier3_fuzzy
from regintel.config import ClusteringConfig
from regintel.models.cluster import Cluster
from regintel.models.failure import Failure


def cluster_failures(
    failures: Sequence[Failure],
    config: ClusteringConfig,
) -> list[Cluster]:
    failures_by_id = {f.occurrence_id: f for f in failures}

    clusters = tier1_signature_exact(failures)

    if config.enable_tier2:
        clusters = tier2_structural(clusters, failures_by_id, config)

    if config.enable_tier3:
        clusters = tier3_fuzzy(clusters, failures_by_id, config)

    return _finalize(clusters)


def _finalize(clusters: list[Cluster]) -> list[Cluster]:
    return sorted(clusters, key=lambda c: (-c.size, c.cluster_id))
