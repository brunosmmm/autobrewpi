from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

HalMode = Literal["mock", "live"]
Direction = Literal["input", "output"]
DType = Literal["float", "bool"]


@dataclass(frozen=True)
class HalChannel:
    name: str
    direction: Direction
    dtype: DType


class Hal(Protocol):
    mode: HalMode

    def list_channels(self) -> list[HalChannel]: ...

    def get(self, name: str) -> float | bool | None: ...

    def set(self, name: str, value: float | bool) -> None: ...
