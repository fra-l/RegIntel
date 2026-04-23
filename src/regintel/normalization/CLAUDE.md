# Normalization — CLAUDE.md

## Two modules, one concern

- `rules.py` — ordered substitution rules that transform a raw message into a normalized message.
- `signature.py` — hashes (normalized message + structural fields) into a stable `signature_id`.

## Rule ordering is load-bearing

Rules are applied in sequence. Order matters — a wrong ordering silently mis-normalizes messages, producing wrong signatures and wrong clusters. Current required order:

1. ANSI color codes → `""` (must be first; they confuse later regexes)
2. Hex literals `0x...` → `<HEX>` (before generic integers, or `0x1234` becomes `0x<NUM>`)
3. Time literals `123ns`, `1.5ms` → `<TIME>` (before decimals)
4. Array indices `[42]` → `[<N>]`
5. Absolute paths → basename only (before numbers; filenames contain digits)
6. Noisy key=value pairs: `seed=N`, `pid=N`, `user=X`, `host=X`
7. 4+ digit integers → `<NUM>` (timestamps, counters)
8. Remaining integers → `<n>`
9. Whitespace collapse → single space (must be last)

**Never reorder without running the full normalization fixture suite.**

## What NOT to normalize

- **Primary file:line** — captured separately as `SourceLocation`; it reaches the signature through that field.
- **Severity keywords** (`ERROR`, `FATAL`, `WARNING`) — stay in the message.
- **Semantic keywords** (`TIMEOUT`, `OVERFLOW`, `MISMATCH`, `EXPECTED`, `GOT`, `ASSERTION`) — must never be stripped.

## Idempotence is required

`normalize(normalize(s)) == normalize(s)` for all inputs. This is tested with Hypothesis. If a rule breaks idempotence, re-normalization after a rule change will produce different signatures than the first pass — which breaks cross-run history in v1.5.

## Signature version

`SIGNATURE_VERSION = "v1"` in `signature.py`. Bump to `"v2"` when normalization rules change in a way that would silently reassign historical failures to different signatures. The version is stored on every `Failure` so old reports can be re-normalized.

Do not implement migration in MVP — just ensure `raw_message`, `extractor_keys`, and `signature_version` are always stored.

## Per-extractor extra rules

`normalize(message, extra_rules=())` accepts extractor-specific rules chained after the base list. Extractors pass their extras at `build_failure` time. Test extractor extras in the extractor's own test module, not here.
