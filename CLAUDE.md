# RegIntel — CLAUDE.md

## Commands

```bash
uv run pytest                        # run all tests
uv run pytest tests/unit             # unit tests only
uv run pytest tests/integration      # integration tests only
uv run pytest -m evaluation          # clustering quality harness (opt-in)
uv run ruff check .                  # lint
uv run ruff check . --fix            # lint + autofix
uv run mypy src tests                # type check
uv run regintel analyze <manifest>   # run the CLI
```

## Repo layout (one-liner per area)

```
src/regintel/
  models/        — frozen dataclasses; no logic, only data
  ingestion/     — manifest.json parser + log loader
  extractors/    — per-simulator log parsers producing Failure objects
  normalization/ — strip noise from messages, compute stable signatures
  clustering/    — three-tier cascade: signature → structural → fuzzy
  flaky/         — multi-run flakiness detection
  reporting/     — terminal, HTML, JSON outputs
  utils/         — hashing, ordering, logging helpers
tests/
  unit/          — per-module correctness tests
  integration/   — end-to-end pipeline test
  evaluation/    — clustering quality harness with labeled corpus
  fixtures/      — logs, normalization pairs, manifests (version-controlled)
```

## Non-negotiable rules

- **Determinism.** Same input → byte-identical output. Sort before hashing. No `set()` ordering in output paths.
- **No LLMs.** No OpenAI/Anthropic dependencies anywhere in the install path.
- **Verilator only.** Do not add VCS/Questa/Xcelium support without explicit sign-off.
- **No persistence.** No database, no `~/.regintel/` state. Read files, write files, exit.
- **Tests first.** Every module has a corresponding test file. Write the test file before the implementation.
- **Frozen dataclasses.** All models use `@dataclass(frozen=True)`. Never mutate a model.

## Python version and style

- Python 3.11+. Use `StrEnum`, PEP 604 unions (`X | Y`), `tomllib`, `collections.abc` imports.
- Line length 100. ruff + mypy strict must stay green at all times.
- No comments explaining *what* code does. Only comment *why* when it would surprise a reader.

## The only metric that matters

Clustering quality on the evaluation harness (`tests/evaluation/`). Target: pairwise F1 ≥ 0.8, purity ≥ 0.8, completeness ≥ 0.8. If clustering is wrong, the fix is almost always in normalization or extractor structural keys — not in the clustering tier itself.
