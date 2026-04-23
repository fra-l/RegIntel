from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class TestStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIP = "skip"


@dataclass(frozen=True)
class TestResult:
    test_name: str
    seed: int | None
    status: TestStatus
    duration_s: float | None
    log_path: Path


@dataclass(frozen=True)
class Run:
    run_id: str
    timestamp: datetime
    project: str | None
    simulator: str
    commit_sha: str | None
    tests: tuple[TestResult, ...]
    manifest_path: Path
