from dataclasses import dataclass, field


@dataclass
class ClusteringConfig:
    enable_tier2: bool = True
    enable_tier3: bool = True
    tier2_min_similarity: int = 60
    tier3_threshold: int = 85
    tier3_max_cluster_size: int = 5
    fuzzy_algorithm: str = "token_set_ratio"


@dataclass
class Config:
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
