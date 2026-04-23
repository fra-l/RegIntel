# Clustering — CLAUDE.md

## Tier semantics

| Tier | Module | Method | Confidence | When it runs |
|------|--------|--------|------------|--------------|
| 1 | `tier1_signature.py` | `"signature"` | 1.0 | Always |
| 2 | `tier2_structural.py` | `"structural"` | ~0.9 | If `config.enable_tier2` |
| 3 | `tier3_fuzzy.py` | `"fuzzy"` | 0.6–0.85 | If `config.enable_tier3` |

Each tier takes the output of the previous tier as input. Tiers 2 and 3 **merge existing clusters** — they never re-cluster from raw failures.

## Tier 1 is the workhorse

Expect 70–85% of real failures to cluster correctly here via pure `signature_id` groupby. If Tier 1 performance is poor, the fix is upstream: normalization rules or extractor structural keys. Do not reach into Tiers 2/3 until Tier 1 is pulling its weight.

`cluster_id` for Tier 1 clusters equals `signature_id`. For Tier 2/3 merged clusters, it is a `stable_hash` of sorted member `occurrence_id`s, computed in `clustering/_helpers.py`.

## Shared helpers (`_helpers.py`)

`common_location(failures)` and `merge_clusters(clusters, failures_by_id, method, tier, confidence)` are shared by Tier 2 and Tier 3 to avoid duplication. `merge_clusters` produces the deterministic merged cluster ID and picks the lex-smallest `occurrence_id` as representative.

## Determinism requirements

- Sort failures by `occurrence_id` before grouping in Tier 1.
- Sort clusters by `(-size, cluster_id)` for output.
- `member_failure_ids` and `affected_tests` must always be sorted tuples.
- `representative_failure_id` is the lexicographically smallest `occurrence_id` in the cluster.
- Never rely on dict or set iteration order anywhere in the clustering path.

## Tier 2 safety rails

Structural merge requires:
- Same `file` AND `line` (configurable, default strict).
- Same `extractor`.
- Same `extractor_keys` (exact match — different component paths are different bugs).
- Pairwise text similarity ≥ `config.tier2_min_similarity` (default 60, token_set_ratio).

If `extractor_keys` differ, do **not** merge, even if everything else matches.

## Tier 3: representative-based, never chaining

Single-linkage chaining (A~B, B~C → merge ABC) produces garbage. Tier 3 uses representative-based merging: a candidate joins a group only if it is similar to the **group's representative**, not just to any member.

Never-merge predicates override similarity: different severity, different extractor, different known file, or different `extractor_keys` → do not merge regardless of score.

Confidence scales from 0.6 (at threshold) to 0.85 (at 100 similarity). Capped at 0.85 to signal that fuzzy is inherently heuristic.

## Tiers are individually toggleable

`config.enable_tier2` and `config.enable_tier3` allow disabling tiers for debugging. When a cluster looks wrong, disable tiers from the bottom up to isolate which tier introduced the bad merge.
