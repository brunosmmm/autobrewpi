from __future__ import annotations

from brew_worker.hal.base import HalChannel, HalMode


class MockHal:
    mode: HalMode = "mock"

    def __init__(self, channels: list[HalChannel]):
        self._channels = {c.name: c for c in channels}
        self._values: dict[str, float | bool | None] = {
            c.name: None for c in channels
        }

    def list_channels(self) -> list[HalChannel]:
        return list(self._channels.values())

    def get(self, name: str) -> float | bool | None:
        if name not in self._channels:
            raise KeyError(name)
        return self._values[name]

    def set(self, name: str, value: float | bool) -> None:
        if name not in self._channels:
            raise KeyError(name)
        ch = self._channels[name]
        if ch.dtype == "bool" and not isinstance(value, bool):
            raise TypeError(f"{name} expects bool")
        if ch.dtype == "float" and not isinstance(value, (int, float)):
            raise TypeError(f"{name} expects float")
        self._values[name] = float(value) if ch.dtype == "float" else value
