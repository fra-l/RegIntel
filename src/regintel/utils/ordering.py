from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def sorted_tuple(items: Iterable[T]) -> tuple[T, ...]:
    return tuple(sorted(items))  # type: ignore[type-var]
