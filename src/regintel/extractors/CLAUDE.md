# Extractors — CLAUDE.md

## Priority ordering

Lower number = runs first. Specific extractors must come before generic ones.

| Extractor | Priority |
|-----------|----------|
| `uvm`     | 10       |
| `sva`     | 20       |
| `verilator` | 30     |
| `generic` | 100 (always last, always matches) |

## Registration

Each extractor calls `register(MyExtractor())` at module level. `extractors/__init__.py` imports all extractor modules to guarantee registration runs on package import. When adding a new extractor, add the import there.

## The Extractor protocol (`base.py`)

Three methods drive block assembly:
- `can_handle(test, log_head)` — cheap check on first ~100 log lines; determines which extractor owns this log.
- `is_primary(line)` — true if this line starts a new failure block.
- `is_continuation(line, block_so_far)` — true if this line extends the current block.

`assemble_blocks()` in `base.py` handles the mechanics. Each extractor only needs to implement the three predicates plus `build_failure()`.

## The SyoSil structural-key requirement (load-bearing)

Two scoreboard instances reporting the same queue name (e.g., `payload_q`) must produce **different** signatures. This is only possible if the scoreboard instance path is captured in `extractor_keys`.

`extractor_keys` flows into `compute_signature()` and separates otherwise-identical normalized messages at Tier 1. If `extractor_keys` is empty when it shouldn't be, the two failures collapse into one cluster — a silent, hard-to-debug over-clustering bug.

The fixture `tests/fixtures/logs/verilator/syosil_two_scoreboards/` is the regression test for this. It must always pass.

## build_failure checklist

Every `build_failure` implementation must:
1. Extract `severity`, `location`, `extractor_keys` from the block.
2. Normalize **the primary line** (not the full block text, unless the extractor has a specific reason).
3. Call `compute_signature(normalized, file, line, severity, extractor_keys)`.
4. Call `compute_occurrence_id(run_id, test_name, seed, log_path, log_line, raw_message)` with `raw_message` (not normalized).
5. Sort `extractor_keys` before storing: `tuple(sorted(extractor_keys))`.
6. Wrap extractor-specific extras in `MappingProxyType({...})` for `raw_fields`.
