# Architecture

RegIntel is a stateless CLI pipeline: it reads files, writes files, and exits. No database, no state directory, no network calls.

## Pipeline

```
manifest.json + log files
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Ingestion                                              │
│  ingestion/manifest.py   parse manifest → Run           │
│  ingestion/loader.py     per-test log → Failure[]       │
└───────────────────┬─────────────────────────────────────┘
                    │  Failure objects
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Normalization  (runs inside loader, per failure)       │
│  normalization/rules.py      strip noise → stable text  │
│  normalization/signature.py  SHA-1 hash → signature_id  │
└───────────────────┬─────────────────────────────────────┘
                    │  Failure objects with signature_ids
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Clustering                                             │
│  Tier 1  signature-exact groupby   (confidence 1.0)     │
│  Tier 2  structural merge          (confidence ~0.9)    │
│  Tier 3  fuzzy text similarity     (confidence 0.6–0.85)│
└───────────────────┬─────────────────────────────────────┘
                    │  Cluster objects
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Reporting                                              │
│  terminal.py   colored Rich output                      │
│  html.py       single self-contained HTML file          │
│  json_export   schema_version: "1.0" JSON               │
└─────────────────────────────────────────────────────────┘
```

## Two-ID scheme

Every `Failure` carries two identifiers:

| ID | Hash inputs | Stability | Purpose |
|----|------------|-----------|---------|
| `occurrence_id` | run_id + test_name + seed + log_path + log_line + raw_message | Per-occurrence | Primary key; cluster membership; future DB PK |
| `signature_id` | signature_version + severity + file + line + normalized_message + sorted(extractor_keys) | Stable across seeds and timestamps | Tier 1 clustering; cross-run history (v1.5) |

The separation means the same bug appearing in 50 different tests produces 50 unique `occurrence_id`s but one shared `signature_id`, so Tier 1 groups them instantly with a single dict lookup.

## Extractor priorities

Extractors run in priority order; the first one whose `can_handle()` returns True owns the entire log.

| Extractor | Priority | `can_handle` check |
|-----------|----------|-------------------|
| UVM | 10 | `"UVM_"` in log head |
| SVA | 20 | assertion pattern in head AND no `"UVM_"` |
| Verilator | 30 | `%Error` or `%Warning` in log head |
| Generic | 100 | always True |

## The SyoSil constraint

Two scoreboard instances reporting the same queue name must produce **different** signatures. This is guaranteed because the component path (e.g., `uvm_test_top.env.axi_sb`) is extracted as an `extractor_key` and hashed into `signature_id` alongside the normalized message. Without this, the failures would collapse into one cluster — a silent over-clustering bug.

The fixture `tests/fixtures/logs/verilator/syosil_two_scoreboards/` and the test `test_syosil_two_scoreboards_different_signatures` are the permanent regression guard for this behavior.

## Clustering tiers

**Tier 1** is the workhorse. Expect 70–85% of real failures to cluster correctly here. If Tier 1 performance is poor, the fix is almost always in normalization rules or extractor structural keys — not in Tiers 2/3.

**Tier 2** handles failures whose normalized messages differ slightly despite sharing the same root cause location (same file:line + extractor + extractor_keys). The pairwise similarity check (default threshold 60) prevents accidental merges of unrelated errors that happen to fire from the same utility line.

**Tier 3** uses representative-based merging, not single-linkage chaining. A candidate joins a group only if it's similar to the *group's representative*, preventing the A→B→C chain where A and C are unrelated. Never-merge predicates (severity, extractor, file, extractor_keys mismatch) override similarity.

## Determinism

Same inputs must produce byte-identical `AnalysisReport` JSON. Achieved by:
- Sorting failures by `occurrence_id` before clustering
- Sorting all collection fields before constructing model objects
- Never relying on dict or set iteration order in output paths
- Tested explicitly: `to_json(result_a) == to_json(result_b)` on identical inputs

## Forward compatibility hooks

`Cluster.cross_run_annotations` and `Run.commit_sha` are reserved for v1.5 cross-run analysis. They are empty/None in v1 but their presence in the schema avoids a breaking change when history support is added.

`Failure.raw_message`, `Failure.extractor_keys`, and `Failure.signature_version` are preserved specifically to support signature re-computation when normalization rules change.

## Adding a simulator

See `docs/extractor_guide.md`. Do not add VCS / Questa / Xcelium support without an explicit decision — each simulator has its own log formats and UVM versions, and the scope cost is not trivial.
