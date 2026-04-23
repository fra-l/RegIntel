from collections.abc import Sequence

from regintel.models.report import FlakyTest
from regintel.models.run import Run, TestStatus

_FAILING = {TestStatus.FAIL, TestStatus.TIMEOUT, TestStatus.ERROR}
_MIN_RUNS = 3


def detect_flaky(runs: Sequence[Run]) -> list[FlakyTest]:
    if len(runs) < _MIN_RUNS:
        return []

    # Collect (test_name, seed) → list of statuses across runs
    from collections import defaultdict

    results: dict[str, list[TestStatus]] = defaultdict(list)
    for run in runs:
        seen: set[str] = set()
        for t in run.tests:
            key = f"{t.test_name}\x1f{t.seed}"
            if key not in seen:
                results[key].append(t.status)
                seen.add(key)

    flaky: list[FlakyTest] = []
    for key, statuses in results.items():
        if len(statuses) < _MIN_RUNS:
            continue
        test_name = key.split("\x1f")[0]
        failures = sum(1 for s in statuses if s in _FAILING)
        if 0 < failures < len(statuses):  # flaky = sometimes passes, sometimes fails
            score = failures / len(statuses)
            flaky.append(
                FlakyTest(
                    test_name=test_name,
                    total_runs=len(statuses),
                    failures=failures,
                    flaky_score=round(score, 3),
                )
            )

    return sorted(flaky, key=lambda f: -f.flaky_score)
