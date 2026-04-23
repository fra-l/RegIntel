import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from regintel.models.run import Run, TestResult, TestStatus
from regintel.utils.hashing import stable_hash


def load_manifest(manifest_path: Path) -> Run:
    manifest_path = manifest_path.resolve()
    raw: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    simulator: str = raw.get("simulator", "verilator")
    project: str | None = raw.get("project")
    commit_sha: str | None = raw.get("commit_sha")

    ts_raw: str | None = raw.get("timestamp")
    if ts_raw:
        timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    else:
        mtime = manifest_path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime, tz=UTC)

    manifest_dir = manifest_path.parent
    test_entries: list[dict[str, Any]] = raw.get("tests", [])
    tests = tuple(
        TestResult(
            test_name=t["test_name"],
            seed=t.get("seed"),
            status=TestStatus(t["status"]),
            duration_s=t.get("duration_s"),
            log_path=(manifest_dir / t["log_path"]).resolve(),
        )
        for t in sorted(test_entries, key=lambda t: (t["test_name"], t.get("seed", 0)))
    )

    run_id = stable_hash(
        "\x1f".join(
            [
                str(manifest_path),
                timestamp.isoformat(),
                *sorted(t.test_name for t in tests),
            ]
        )
    )

    return Run(
        run_id=run_id,
        timestamp=timestamp,
        project=project,
        simulator=simulator,
        commit_sha=commit_sha,
        tests=tests,
        manifest_path=manifest_path,
    )
