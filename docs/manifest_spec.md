# Manifest Specification

RegIntel requires a `manifest.json` file alongside your log directory.

## Minimal example

```json
{
  "simulator": "verilator",
  "timestamp": "2026-04-23T10:00:00Z",
  "tests": [
    {
      "test_name": "axi_sanity",
      "seed": 42,
      "status": "fail",
      "log_path": "logs/axi_sanity.log"
    }
  ]
}
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `simulator` | string | yes | Must be `"verilator"` for MVP |
| `timestamp` | ISO 8601 string | no | Run timestamp; falls back to manifest file mtime |
| `project` | string | no | Free-form project label |
| `commit_sha` | string | no | Git SHA for cross-run correlation (v1.5) |
| `tests` | array | yes | One entry per test |
| `tests[].test_name` | string | yes | Unique test identifier |
| `tests[].seed` | integer | no | Random seed |
| `tests[].status` | string | yes | `pass`, `fail`, `timeout`, `error`, `skip` |
| `tests[].duration_s` | float | no | Wall-clock duration in seconds |
| `tests[].log_path` | string | yes | Path to log file, relative to manifest |
