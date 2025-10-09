from __future__ import annotations
from typing import Any, Iterator, Mapping, MutableMapping, Sequence
from types import MappingProxyType


class ReadOnlyList(Sequence[Any]):
    __slots__ = ("_data",)
    def __init__(self, data: Sequence[Any]) -> None:
        self._data = tuple(data)
    def __len__(self) -> int: return len(self._data)
    def __getitem__(self, i: int) -> Any: return self._data[i]
    def __iter__(self) -> Iterator[Any]: return iter(self._data)
    def __repr__(self) -> str: return f"ReadOnlyList({self._data!r})"


def freeze(obj: Any) -> Any:
    match obj:
        case dict():
            return MappingProxyType({k: freeze(v) for k, v in obj.items()})
        case list():
            return ReadOnlyList([freeze(v) for v in obj])
        case tuple():
            return ReadOnlyList([freeze(v) for v in obj])  # simple choice
    return obj

