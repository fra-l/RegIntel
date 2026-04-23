from pathlib import Path

from regintel.extractors import generic, registry, sva, uvm, verilator  # noqa: F401
from regintel.extractors.base import assemble_blocks
from regintel.ingestion.manifest import load_manifest
from regintel.models.failure import Failure
from regintel.models.run import Run, TestStatus
from regintel.utils.logging import logger

_FAILING_STATUSES = {TestStatus.FAIL, TestStatus.TIMEOUT, TestStatus.ERROR}
_LOG_HEAD_LINES = 100


def load_run(manifest_path: Path) -> tuple[Run, list[Failure]]:
    run = load_manifest(manifest_path)
    failures: list[Failure] = []

    for test in run.tests:
        if test.status not in _FAILING_STATUSES:
            continue
        if not test.log_path.exists():
            logger.warning("Log file not found: %s", test.log_path)
            continue

        try:
            log_text = test.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Could not read log %s: %s", test.log_path, exc)
            continue

        log_lines = log_text.splitlines()
        log_head = "\n".join(log_lines[:_LOG_HEAD_LINES])

        extractor = registry.select_extractor(test, log_head)

        for block in assemble_blocks(extractor, log_lines):
            try:
                failure = extractor.build_failure(block, test, run.run_id, log_lines)
                failures.append(failure)
            except Exception as exc:
                logger.warning(
                    "Extractor %s failed on block at line %d in %s: %s",
                    extractor.name,
                    block.primary_line_no,
                    test.log_path,
                    exc,
                )

    return run, failures
