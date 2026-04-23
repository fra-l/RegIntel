# Minimal Example

Five tests, two failures — the smallest complete RegIntel demo. Ships in the repo so you can try it without any real regression data.

## Run it

```bash
regintel analyze examples/minimal/manifest.json --html minimal.html
```

Open `minimal.html` in any browser.

## What it demonstrates

- Two failing tests (`axi_corner` and `mem_basic`) both produce the same UVM_ERROR about a bus stall.
- RegIntel extracts the error from each log, normalizes the timestamps and addresses away, and groups both failures into **one cluster** with `confidence 1.00`.
- Three passing tests (`axi_sanity`, `axi_stress`, `mem_stress`) produce no failures.

## Files

```
examples/minimal/
├── manifest.json        — lists all 5 tests and their log paths
└── logs/
    ├── axi_sanity.log   — pass
    ├── axi_stress.log   — pass
    ├── axi_corner.log   — fail: UVM_ERROR bus stall
    ├── mem_basic.log    — fail: UVM_ERROR bus stall (same bug, different seed)
    └── mem_stress.log   — pass
```

## Understanding the output

The terminal summary shows:

```
╭─ RegIntel Analysis ────────────────────────────────────────╮
│ 5 tests · 2 failures · 1 cluster · analyzed in 0.0s        │
╰────────────────────────────────────────────────────────────╯
```

One cluster means RegIntel correctly determined that both failures share the same root cause (the bus driver stall bug in `my_driver.sv:42`), even though they came from different tests with different seeds and different timestamps in the log.

## Using with real data

Replace `examples/minimal/manifest.json` with your own manifest pointing at your Verilator regression logs. See [`docs/manifest_spec.md`](../../docs/manifest_spec.md) for the full schema.
