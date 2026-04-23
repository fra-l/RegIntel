# Log Fixtures

Each subdirectory under `verilator/` exercises a specific extraction scenario.

## Adding a fixture

1. Create a directory under `verilator/<scenario_name>/`.
2. Add `test.log` — the raw Verilator log fragment.
3. Add `expected.json` — the expected list of serialized `Failure` objects.
4. Add `README.md` — one line describing what this fixture exercises.

Never delete a fixture. If expected output changes, update `expected.json` and explain why in the commit message.
