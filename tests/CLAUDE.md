# Tests — CLAUDE.md

## Three layers

| Layer | Location | Purpose |
|-------|----------|---------|
| Unit | `tests/unit/` | Per-module correctness; fast; run on every commit |
| Integration | `tests/integration/` | End-to-end pipeline on curated fixtures |
| Evaluation | `tests/evaluation/` | Quantitative clustering quality; opt-in (`-m evaluation`) |

## Fixture discipline (strict)

- **Never delete a fixture.** If expected output changes legitimately, update the expected file and explain why in the commit message.
- **Write fixtures from real bugs.** When a user reports wrong clustering: add their log as a fixture first, write a failing test, then fix. The fixture + test + fix ship together.
- **Fixtures are documentation.** Directory name and README.md should make the scenario obvious to someone reading the repo cold.
- All fixtures are version-controlled. Nothing under `tests/fixtures/` is gitignored.

## Fixture locations

```
tests/fixtures/
  normalization/          — *.input.txt / *.expected.txt pairs for the rule engine
  signature_stability/    — groups of variants that MUST produce the same signature
  signature_separation/   — groups of variants that MUST produce DIFFERENT signatures
  logs/verilator/         — raw logs per extraction scenario
  manifests/              — manifest.json files for integration tests
```

Reporter tests (`tests/unit/test_reporting/`) use in-memory `AnalysisReport` fixtures defined in their `conftest.py` rather than file-based golden fixtures. Add file-based golden fixtures there only if the in-memory approach becomes unwieldy.

## Determinism tests

Every module that produces IDs, clusters, or reports needs a determinism test:

```python
def test_output_is_deterministic() -> None:
    a = run(fixture)
    b = run(fixture)
    assert a == b
    assert to_json(a) == to_json(b)  # byte-identical serialization
```

A stray `set()` or unsorted dict iteration shows up here.

## The SyoSil regression test

`tests/fixtures/logs/verilator/syosil_two_scoreboards/` — two scoreboard instances with the same queue name must produce **different** signatures. This test must stay green at all times. It is the load-bearing regression test for extractor structural keys.

## Evaluation harness gate

`pytest -m evaluation` must report:
- Pairwise F1 ≥ 0.8
- Weighted cluster purity ≥ 0.8
- Weighted cluster completeness ≥ 0.8

**Current baseline (0.1.0): F1 = 1.000, purity = 1.000, completeness = 1.000** on 16 labeled failures across 3 runs. Update this line when the corpus grows.

If metrics fall below the gate, the fix is almost always in normalization or extractor keys — not in clustering thresholds. Tune thresholds only after upstream layers are correct.

## Parametrize aggressively

Use `@pytest.mark.parametrize` for data-driven cases — especially normalization fixtures (all `*.input.txt` files discovered automatically) and round-trip tests (all model types).
