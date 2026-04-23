# Changelog

All notable changes to RegIntel are documented here.

## [0.1.0] — 2026-04-23

Initial release. MVP feature set.

### Added

**Ingestion**
- `manifest.json` parser: reads simulator, timestamp, commit SHA, and per-test status + log path.
- Log loader: selects the appropriate extractor per log, assembles multi-line failure blocks, returns `Failure` objects.

**Extractors**
- `UVMExtractor` (priority 10): parses `UVM_ERROR / UVM_FATAL / UVM_WARNING` lines. Extracts component path and tag as structural keys so different scoreboard instances never collapse into one cluster.
- `SVAExtractor` (priority 20): parses `Assertion failed for property …` lines. Extracts property name as structural key.
- `VerilatorExtractor` (priority 30): parses `%Error` and `%Warning` lines. Extracts message type code (e.g., `UNUSED`, `STMTDLY`).
- `GenericExtractor` (priority 100, always matches): fallback for logs that match no specific extractor.

**Normalization**
- Nine-rule ordered pipeline: ANSI codes → hex literals → time literals → array indices → absolute paths → key=value noise → 4+ digit integers → small integers → whitespace collapse.
- Idempotent by design; verified with Hypothesis property tests.
- `SIGNATURE_VERSION = "v1"` stored on every `Failure` to enable future re-normalization.

**Clustering**
- Tier 1 — signature-exact: pure groupby on `signature_id`; confidence 1.0.
- Tier 2 — structural merge: groups Tier 1 clusters sharing the same severity + file + line + extractor + extractor_keys; requires pairwise text similarity ≥ 60; confidence 0.9.
- Tier 3 — fuzzy text similarity: representative-based greedy merging (no chaining); blocking by severity + extractor + first significant token; never-merge predicates for severity/extractor/file/key mismatches; confidence 0.6–0.85.
- All tiers independently toggleable via `ClusteringConfig`.
- Deterministic: same input → byte-identical output.

**Reporting**
- Terminal (`rich`): colored panels, confidence badges, FUZZY label for Tier 3 clusters, `--top` / `--verbose` flags, non-zero exit code for CI integration.
- HTML: single self-contained file, no CDN dependencies, light/dark mode via CSS custom properties, expandable `<details>` cluster cards with log context, inline JS text search.
- JSON: `schema_version: "1.0"` envelope, pretty-printed by default, stable field set.

**CLI**
- `regintel analyze MANIFEST` with `--html`, `--json`, `--terminal-only`, `--top`, `--verbose`, `--fail-on`, `--config`.
- TOML config file support for clustering thresholds.

**Evaluation harness**
- Pairwise F1, weighted purity, and weighted completeness computed from first principles (no sklearn).
- Three labeled runs (16 failures total): bus-stall regression, SyoSil two-scoreboards, mixed failure types.
- Quality gate: F1 ≥ 0.8, purity ≥ 0.8, completeness ≥ 0.8. Current result: **F1 = 1.000** on all three runs.

### Technical

- Python 3.11+. Dependencies: `rapidfuzz`, `jinja2`, `rich`, `click`.
- `mypy --strict` clean. `ruff` clean. 87% test coverage.
- 205 tests: unit, integration, evaluation harness.
