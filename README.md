# RegIntel

**Regression intelligence for chip verification.**  
Reads Verilator logs and turns hundreds of failures into a handful of root-cause clusters — in under 60 seconds.

```
37 failures  →  3 clusters  ·  analyzed in 14.2s
```

## Install

```bash
uv venv && uv sync
```

Requires Python 3.11+. No cloud uploads, no LLM calls, no external dependencies beyond the package.

## 60-second demo

```bash
# Point RegIntel at your Verilator regression
regintel analyze path/to/manifest.json

# Write an HTML report too
regintel analyze path/to/manifest.json --html report.html

# Try the bundled minimal example
regintel analyze examples/minimal/manifest.json --html minimal.html
```

Terminal output:

```
╭─ RegIntel Analysis ────────────────────────────────────────╮
│ 5 tests · 2 failures · 1 cluster · analyzed in 0.0s        │
╰────────────────────────────────────────────────────────────╯

Top clusters (1):

  Cluster 1  ·  2 failures  ·  confidence 1.00
  UVM_ERROR my_driver.sv(<n>) @ <TIME>: … [DRV] Bus stalled waiting for grant
  at my_driver.sv:42
  affects failing_test_a
```

Open `report.html` in any browser for the full analysis with expandable failure details and log context.

## How it works

RegIntel runs a three-stage pipeline:

1. **Extract** — reads each log with the appropriate extractor (UVM, SVA, Verilator, or generic fallback), assembles multi-line failure blocks, pulls out structural keys (component path, assertion name, scoreboard instance).
2. **Normalize** — strips timestamps, addresses, array indices, and other run-specific noise to produce a stable message signature.
3. **Cluster** — three-tier cascade: exact-signature match → structural merge → fuzzy text similarity. Two failures reporting the same bug from different test seeds always land in the same cluster.

## Manifest format

RegIntel needs a `manifest.json` alongside your log directory:

```json
{
  "simulator": "verilator",
  "timestamp": "2026-04-23T10:00:00Z",
  "tests": [
    { "test_name": "axi_sanity", "seed": 42, "status": "fail",
      "log_path": "logs/axi_sanity.log" }
  ]
}
```

See [`docs/manifest_spec.md`](docs/manifest_spec.md) for the full schema.

## CLI reference

```
regintel analyze MANIFEST [OPTIONS]

  --html PATH          Write HTML report (default: regintel-report.html)
  --json PATH          Write JSON export
  --terminal-only      Skip file outputs
  --top N              Clusters shown in terminal summary (default: 10)
  --verbose            Show all clusters and member details
  --fail-on any|new|none  Exit code policy for CI (default: any)
  --config PATH        Load settings from a TOML file
```

Exit code is non-zero when clusters are found (`--fail-on any`), enabling zero-config CI integration.

## Adding a new extractor

See [`docs/extractor_guide.md`](docs/extractor_guide.md). In short: implement the `Extractor` protocol, register it, add fixtures.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full pipeline description and design decisions.

## Development

```bash
uv sync --extra dev          # install with dev extras
uv run pytest                # all tests
uv run pytest -m evaluation  # clustering quality harness
uv run ruff check .          # lint
uv run mypy src tests        # type check
```

Coverage target: ≥ 80%.

## License

MIT © Francesco Laezza
