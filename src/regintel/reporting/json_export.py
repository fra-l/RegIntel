from pathlib import Path

from regintel.models.report import AnalysisReport
from regintel.models.serialization import to_json as _to_json


def to_json(report: AnalysisReport, indent: int = 2) -> str:
    return _to_json(report, indent=indent)


def write_json(report: AnalysisReport, output_path: Path, indent: int = 2) -> None:
    output_path.write_text(_to_json(report, indent=indent), encoding="utf-8")
