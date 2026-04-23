import time
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import regintel
from regintel.clustering.cascade import cluster_failures
from regintel.config import Config
from regintel.flaky.detector import detect_flaky
from regintel.ingestion.loader import load_run
from regintel.models.report import AnalysisReport
from regintel.utils.hashing import stable_hash

_SEP = "\x1f"


def analyze(
    manifest_path: Path,
    config: Config | None = None,
) -> AnalysisReport:
    if config is None:
        config = Config()

    t0 = time.monotonic()

    run, failures = load_run(manifest_path)
    clusters = cluster_failures(failures, config.clustering)
    flaky_tests = detect_flaky((run,))

    duration = round(time.monotonic() - t0, 3)

    extractor_usage: dict[str, int] = {}
    for f in failures:
        extractor_usage[f.extractor] = extractor_usage.get(f.extractor, 0) + 1

    stats: dict[str, object] = {
        "total_tests": len(run.tests),
        "total_failures": len(failures),
        "total_clusters": len(clusters),
        "tier1_clusters": sum(1 for c in clusters if c.tier == 1),
        "tier2_merges": sum(1 for c in clusters if c.tier == 2),
        "tier3_merges": sum(1 for c in clusters if c.tier == 3),
        "analysis_duration_s": duration,
        "extractor_usage": extractor_usage,
    }

    cc = config.clustering
    config_snap: dict[str, object] = {
        "normalization_version": "v1",
        "clustering": {
            "enable_tier2": cc.enable_tier2,
            "enable_tier3": cc.enable_tier3,
            "tier2_min_similarity": cc.tier2_min_similarity,
            "tier3_threshold": cc.tier3_threshold,
            "tier3_max_cluster_size": cc.tier3_max_cluster_size,
            "fuzzy_algorithm": cc.fuzzy_algorithm,
        },
    }

    report_id = stable_hash(_SEP.join([run.run_id, regintel.__version__]))

    return AnalysisReport(
        report_id=report_id,
        generated_at=datetime.now(tz=UTC),
        tool_version=regintel.__version__,
        config_snapshot=MappingProxyType(config_snap),
        runs=(run,),
        failures=tuple(sorted(failures, key=lambda f: f.occurrence_id)),
        clusters=tuple(clusters),
        flaky_tests=tuple(flaky_tests),
        stats=MappingProxyType(stats),
    )
