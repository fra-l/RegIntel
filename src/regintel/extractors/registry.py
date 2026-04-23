from collections.abc import Sequence

from regintel.extractors.base import Extractor
from regintel.models.run import TestResult

_REGISTRY: list[Extractor] = []


def register(extractor: Extractor) -> None:
    _REGISTRY.append(extractor)
    _REGISTRY.sort(key=lambda e: e.priority)


def select_extractor(test: TestResult, log_head: str) -> Extractor:
    for extractor in _REGISTRY:
        if extractor.can_handle(test, log_head):
            return extractor
    raise RuntimeError("No extractor matched (generic extractor should always match)")


def all_extractors() -> Sequence[Extractor]:
    return tuple(_REGISTRY)
