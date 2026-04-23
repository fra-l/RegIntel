# OpenTitan Demo

This example uses real OpenTitan regression data, which is not committed to this repo.

To run this demo, obtain a set of Verilator regression logs from an OpenTitan CI run and place them alongside a `manifest.json` following the schema in `docs/manifest_spec.md`.

Then run:

```bash
regintel analyze path/to/manifest.json --html report.html
```
