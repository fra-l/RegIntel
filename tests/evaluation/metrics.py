"""Clustering quality metrics for the evaluation harness.

All metrics are computed from scratch to avoid sklearn dependency.

Ground truth and predicted are both mappings from failure_id to label/cluster_id.
Only failure_ids present in both mappings are considered.
"""

from dataclasses import dataclass
from itertools import combinations


@dataclass
class ClusteringMetrics:
    pairwise_precision: float
    pairwise_recall: float
    pairwise_f1: float
    weighted_purity: float
    weighted_completeness: float
    n_failures: int
    n_pred_clusters: int
    n_gt_clusters: int

    def passes_gate(
        self,
        min_f1: float = 0.8,
        min_purity: float = 0.8,
        min_completeness: float = 0.8,
    ) -> bool:
        return (
            self.pairwise_f1 >= min_f1
            and self.weighted_purity >= min_purity
            and self.weighted_completeness >= min_completeness
        )

    def summary(self) -> str:
        return (
            f"F1={self.pairwise_f1:.3f}  "
            f"P={self.pairwise_precision:.3f}  "
            f"R={self.pairwise_recall:.3f}  "
            f"purity={self.weighted_purity:.3f}  "
            f"completeness={self.weighted_completeness:.3f}  "
            f"({self.n_failures} failures, "
            f"{self.n_pred_clusters} pred / {self.n_gt_clusters} gt clusters)"
        )


@dataclass
class DiagnosticRow:
    kind: str          # "pred_cluster" or "gt_cluster"
    label: str
    size: int
    dominant_label: str
    dominant_count: int
    purity_or_completeness: float


def compute_metrics(
    ground_truth: dict[str, str],
    predicted: dict[str, str],
) -> ClusteringMetrics:
    """Compute pairwise and set-based metrics.

    Args:
        ground_truth: failure_id → ground-truth cluster label
        predicted:    failure_id → predicted cluster id
    """
    common_ids = sorted(set(ground_truth) & set(predicted))
    n = len(common_ids)

    if n == 0:
        return ClusteringMetrics(1.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0)

    # --- pairwise ---
    tp = fp = fn = 0
    for a, b in combinations(common_ids, 2):
        same_gt = ground_truth[a] == ground_truth[b]
        same_pred = predicted[a] == predicted[b]
        if same_gt and same_pred:
            tp += 1
        elif same_pred:
            fp += 1
        elif same_gt:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # --- purity: for each predicted cluster, fraction from dominant GT class ---
    pred_groups: dict[str, list[str]] = {}
    for fid in common_ids:
        pred_groups.setdefault(predicted[fid], []).append(fid)

    purity_sum = 0.0
    for members in pred_groups.values():
        gt_counts: dict[str, int] = {}
        for fid in members:
            gt_counts[ground_truth[fid]] = gt_counts.get(ground_truth[fid], 0) + 1
        purity_sum += max(gt_counts.values())
    weighted_purity = purity_sum / n

    # --- completeness: for each GT cluster, fraction in dominant predicted cluster ---
    gt_groups: dict[str, list[str]] = {}
    for fid in common_ids:
        gt_groups.setdefault(ground_truth[fid], []).append(fid)

    completeness_sum = 0.0
    for members in gt_groups.values():
        pred_counts: dict[str, int] = {}
        for fid in members:
            pred_counts[predicted[fid]] = pred_counts.get(predicted[fid], 0) + 1
        completeness_sum += max(pred_counts.values())
    weighted_completeness = completeness_sum / n

    return ClusteringMetrics(
        pairwise_precision=round(precision, 4),
        pairwise_recall=round(recall, 4),
        pairwise_f1=round(f1, 4),
        weighted_purity=round(weighted_purity, 4),
        weighted_completeness=round(weighted_completeness, 4),
        n_failures=n,
        n_pred_clusters=len(pred_groups),
        n_gt_clusters=len(gt_groups),
    )


def diagnose(
    ground_truth: dict[str, str],
    predicted: dict[str, str],
) -> list[DiagnosticRow]:
    """Per-cluster breakdown for debugging low scores."""
    common_ids = sorted(set(ground_truth) & set(predicted))

    pred_groups: dict[str, list[str]] = {}
    for fid in common_ids:
        pred_groups.setdefault(predicted[fid], []).append(fid)

    gt_groups: dict[str, list[str]] = {}
    for fid in common_ids:
        gt_groups.setdefault(ground_truth[fid], []).append(fid)

    rows: list[DiagnosticRow] = []

    for pred_label, members in sorted(pred_groups.items()):
        gt_counts: dict[str, int] = {}
        for fid in members:
            gt_counts[ground_truth[fid]] = gt_counts.get(ground_truth[fid], 0) + 1
        dominant = max(gt_counts, key=lambda k: gt_counts[k])
        rows.append(DiagnosticRow(
            kind="pred_cluster",
            label=pred_label[:12],
            size=len(members),
            dominant_label=dominant,
            dominant_count=gt_counts[dominant],
            purity_or_completeness=gt_counts[dominant] / len(members),
        ))

    for gt_label, members in sorted(gt_groups.items()):
        pred_counts: dict[str, int] = {}
        for fid in members:
            pred_counts[predicted[fid]] = pred_counts.get(predicted[fid], 0) + 1
        dominant = max(pred_counts, key=lambda k: pred_counts[k])
        rows.append(DiagnosticRow(
            kind="gt_cluster",
            label=gt_label,
            size=len(members),
            dominant_label=dominant[:12],
            dominant_count=pred_counts[dominant],
            purity_or_completeness=pred_counts[dominant] / len(members),
        ))

    return rows


def aggregate(metrics_list: list[ClusteringMetrics]) -> ClusteringMetrics:
    """Weighted aggregate across runs (weighted by n_failures)."""
    if not metrics_list:
        return ClusteringMetrics(1.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0)

    total = sum(m.n_failures for m in metrics_list)
    if total == 0:
        return ClusteringMetrics(1.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0)

    def _w(attr: str) -> float:
        return float(sum(getattr(m, attr) * m.n_failures for m in metrics_list)) / total

    return ClusteringMetrics(
        pairwise_precision=round(_w("pairwise_precision"), 4),
        pairwise_recall=round(_w("pairwise_recall"), 4),
        pairwise_f1=round(_w("pairwise_f1"), 4),
        weighted_purity=round(_w("weighted_purity"), 4),
        weighted_completeness=round(_w("weighted_completeness"), 4),
        n_failures=total,
        n_pred_clusters=sum(m.n_pred_clusters for m in metrics_list),
        n_gt_clusters=sum(m.n_gt_clusters for m in metrics_list),
    )
