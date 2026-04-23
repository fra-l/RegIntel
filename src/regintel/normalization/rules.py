import re
from collections.abc import Iterable
from itertools import chain
from typing import NamedTuple


class Rule(NamedTuple):
    pattern: re.Pattern[str]
    replacement: str


def _r(pattern: str, replacement: str, flags: int = 0) -> Rule:
    return Rule(re.compile(pattern, flags), replacement)


# Order is load-bearing — see normalization/CLAUDE.md for the invariants.
_RULES: list[Rule] = [
    # 1. ANSI color/control codes (must be first)
    _r(r"\x1b\[[0-9;]*[mGKHF]", ""),

    # 2. Hex literals (before generic integers)
    _r(r"0[xX][0-9a-fA-F]+", "<HEX>"),

    # 3. Time literals (before generic integers and decimals)
    _r(r"\d+(?:\.\d+)?\s*(?:ns|us|ms|ps|fs)\b", "<TIME>", re.IGNORECASE),

    # 4. Array indices (before generic integers)
    _r(r"\[\d+\]", "[<N>]"),

    # 5. Absolute paths → basename only (before integers; filenames contain digits)
    _r(r"(?:/[^\s/]+)+/([^\s/]+)", r"\1"),

    # 6. Noisy key=value pairs
    _r(r"\bseed\s*=\s*\d+", "seed=<N>", re.IGNORECASE),
    _r(r"\bpid\s*=\s*\d+", "pid=<N>", re.IGNORECASE),
    _r(r"\buser\s*=\s*\S+", "user=<USER>", re.IGNORECASE),
    _r(r"\bhost\s*=\s*\S+", "host=<HOST>", re.IGNORECASE),

    # 7. 4+ digit integers (timestamps, counters) — before small integers
    _r(r"\b\d{4,}\b", "<NUM>"),

    # 8. Remaining small integers
    _r(r"\b\d+\b", "<n>"),
]


def normalize(message: str, extra_rules: Iterable[Rule] = (), max_len: int = 512) -> str:
    first_line = message.splitlines()[0] if message else ""
    s = first_line[:max_len]

    for rule in chain(_RULES, extra_rules):
        s = rule.pattern.sub(rule.replacement, s)

    # 9. Whitespace collapse (always last)
    return " ".join(s.split())
