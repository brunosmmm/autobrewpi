from __future__ import annotations

from typing import Any

from brew_worker.runtime.block import Block


class GpioOut(Block):
    type_name = "GpioOut"
    inputs = {"Value": "bool"}
    outputs: dict[str, str] = {}

    def __init__(self, name: str, hal: Any = None, **params):
        self._hal = hal
        super().__init__(name, **params)

    def cycle(self) -> None:
        channel = self._params.get("channel")
        if channel is None or self._hal is None:
            return
        value = self.get_input("Value")
        if value is None:
            return
        self._hal.set(channel, bool(value))
