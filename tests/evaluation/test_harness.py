"""Evaluation harness integration test.

Marked @pytest.mark.evaluation — opt-in for CI, but surface metrics on every PR.
Run with:  pytest tests/evaluation -v -m evaluation

Quality gate: pairwise F1 ≥ 0.8, weighted purity ≥ 0.8, weighted completeness ≥ 0.8.
If the gate fails, diagnose which runs are below par before tuning thresholds.
"""

import pytest

from tests.evaluation.harness import run_evaluation

_GATE_F1 = 0.8
_GATE_PURITY = 0.8
_GATE_COMPLETENESS = 0.8


@pytest.mark.evaluation
def test_evaluation_harness_quality_gate() -> None:
    report = run_evaluation()
    report.print_summary()

    agg = report.aggregate_metrics
    assert agg.pairwise_f1 >= _GATE_F1, (
        f"Pairwise F1 {agg.pairwise_f1:.3f} is below gate {_GATE_F1}. "
        f"Diagnose which runs are failing and check normalization / extractor keys."
    )
    assert agg.weighted_purity >= _GATE_PURITY, (
        f"Weighted purity {agg.weighted_purity:.3f} is below gate {_GATE_PURITY}. "
        f"Over-clustering: predicted clusters contain members from multiple GT classes."
    )
    assert agg.weighted_completeness >= _GATE_COMPLETENESS, (
        f"Weighted completeness {agg.weighted_completeness:.3f} below gate "
        f"{_GATE_COMPLETENESS}: GT clusters split across predicted clusters."
    )


@pytest.mark.evaluation
def test_evaluation_per_run_metrics() -> None:
    """Individual run breakdown — shows which runs contribute to low scores."""
    report = run_evaluation()
    for run_result in report.run_results:
        m = run_result.metrics
        print(f"\n  {run_result.description}")
        print(f"    {m.summary()}")
        # Each individual run should also pass the gate
        assert m.pairwise_f1 >= _GATE_F1, (
            f"Run '{run_result.description}' F1={m.pairwise_f1:.3f} below gate. "
            f"manifest: {run_result.manifest_path}"
        )


@pytest.mark.evaluation
def test_labeled_corpus_has_minimum_failures() -> None:
    """The corpus must have ≥ 10 labeled failures to be a meaningful sample."""
    report = run_evaluation()
    total = report.aggregate_metrics.n_failures
    assert total >= 10, (
        f"Labeled corpus only has {total} failures. "
        f"Add more labeled runs to make the evaluation meaningful."
    )
