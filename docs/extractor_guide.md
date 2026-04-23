# Extractor Guide

This guide explains how to add a new extractor for a log format RegIntel doesn't support yet.

## Background

An extractor converts raw log lines into `Failure` objects. The critical design constraint: errors are **blocks**, not lines. A primary line starts a block; continuation lines (indented details, expected-vs-actual output, timing info) belong to it. If the extractor emits only primary lines, structurally distinct failures may collapse into one cluster.

## Steps

### 1. Create the module

Add `src/regintel/extractors/<name>.py`. Implement the `Extractor` protocol from `extractors/base.py`:

```python
from collections.abc import Sequence
from types import MappingProxyType

from regintel.extractors.base import FailureBlock, context_lines
from regintel.extractors.registry import register
from regintel.models.failure import Failure, Severity, SourceLocation
from regintel.models.run import TestResult
from regintel.normalization.rules import normalize
from regintel.normalization.signature import SIGNATURE_VERSION, compute_signature
from regintel.utils.hashing import compute_occurrence_id


class MyExtractor:
    name = "myformat"
    priority = 25          # lower = runs before higher-priority extractors

    def can_handle(self, test: TestResult, log_head: str) -> bool:
        # Cheap check on first ~100 lines of the log.
        # Return True if this log looks like your format.
        return "MY_FORMAT_MARKER" in log_head

    def is_primary(self, line: str) -> bool:
        # True if this line starts a new failure block.
        return line.startswith("MY_ERROR:")

    def is_continuation(self, line: str, block_so_far: Sequence[str]) -> bool:
        # True if this line extends the current block.
        # A blank line or a new primary ends the block.
        if not line.strip():
            return False
        if self.is_primary(line):
            return False
        return line[:1] in (" ", "\t")

    def build_failure(
        self,
        block: FailureBlock,
        test: TestResult,
        run_id: str,
        log_lines: Sequence[str],
    ) -> Failure:
        raw_message = block.primary_line
        if block.continuation_lines:
            raw_message += "\n" + "\n".join(block.continuation_lines)

        # Extract structural information
        severity = Severity.ERROR          # or parse from the line
        location = SourceLocation(file=None, line=None)   # parse if available
        extractor_keys = ()                # tuple of strings; see note below

        normalized = normalize(block.primary_line)
        ctx_before, ctx_after = context_lines(log_lines, block.primary_line_no)

        sig_id = compute_signature(
            normalized_message=normalized,
            file=location.file,
            line=location.line,
            severity=severity,
            extractor_keys=extractor_keys,
        )
        occ_id = compute_occurrence_id(
            run_id=run_id,
            test_name=test.test_name,
            seed=test.seed,
            log_path=test.log_path,
            log_line=block.primary_line_no,
            raw_message=raw_message,   # raw, not normalized
        )

        return Failure(
            occurrence_id=occ_id,
            signature_id=sig_id,
            signature_version=SIGNATURE_VERSION,
            test_name=test.test_name,
            seed=test.seed,
            severity=severity,
            raw_message=raw_message,
            normalized_message=normalized,
            location=location,
            context_before=ctx_before,
            context_after=ctx_after,
            log_path=test.log_path,
            log_line=block.primary_line_no,
            extractor=self.name,
            extractor_keys=extractor_keys,
            raw_fields=MappingProxyType({}),
        )


register(MyExtractor())
```

### 2. Register on import

Add the import to `extractors/__init__.py`:

```python
from regintel.extractors import generic, registry, sva, uvm, verilator, myformat  # add here
```

### 3. Choose the right priority

| Priority | Extractor | When to use |
|----------|-----------|-------------|
| 10 | UVM | UVM-based logs |
| 20 | SVA | Raw assertion output (non-UVM) |
| 25 | *Your extractor* | Between SVA and Verilator |
| 30 | Verilator | Verilator native errors |
| 100 | Generic | Last resort |

Lower number = runs earlier. Pick a priority that places your extractor after more specific formats and before less specific ones.

### 4. Add fixtures

Create `tests/fixtures/logs/verilator/<scenario>/` with:
- `test.log` — a representative raw log fragment
- `README.md` — one line describing what this fixture exercises

Add tests in `tests/unit/test_extractors/test_<name>.py`. At minimum:
- `can_handle` returns True for your format, False for others
- Primary line detection
- Continuation line detection
- `build_failure` produces correct severity, location, and extractor_keys
- Malformed input does not crash (returns zero failures or raises gracefully)

### 5. The extractor_keys requirement

`extractor_keys` must uniquely distinguish failures that share the same error message but come from different structural sources. Examples:

- UVM component path: `uvm_test_top.env.axi_sb` vs `uvm_test_top.env.mem_sb`
- SVA property name: `prop_grant_valid` vs `prop_no_double_grant`
- Verilator message type: `UNUSED` vs `STMTDLY`

If `extractor_keys` is empty when two genuinely different failures share a normalized message, they will collapse into one cluster — a silent over-clustering bug that no amount of Tier 2/3 tuning can fix.

Always `tuple(sorted(extractor_keys))` before storing.

## Testing your extractor

Run the full suite after adding your extractor:

```bash
uv run pytest tests/unit/test_extractors/
uv run pytest -m evaluation   # check clustering quality gate still passes
uv run ruff check .
uv run mypy src tests
```

## What not to do

- **Do not add VCS / Questa / Xcelium support** without an explicit decision. Each simulator has its own log formats, UVM versions, and custom report servers. The scope cost is significant.
- **Do not normalize the primary file:line** in `build_failure` — that information reaches the signature through `SourceLocation`, not through the message text.
- **Do not strip semantic keywords** (`TIMEOUT`, `OVERFLOW`, `MISMATCH`, `EXPECTED`, `GOT`, `ASSERTION`) in normalization rules.
