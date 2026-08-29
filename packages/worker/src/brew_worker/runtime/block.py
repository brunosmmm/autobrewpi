from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class Block(ABC):
    type_name: ClassVar[str]
    inputs: ClassVar[dict[str, str]] = {}
    outputs: ClassVar[dict[str, str]] = {}

    def __init__(self, name: str, **params: Any):
        self.name = name
        self._input_values: dict[str, Any] = {k: None for k in self.inputs}
        self._output_values: dict[str, Any] = {k: None for k in self.outputs}
        self.apply_params(params)

    def apply_params(self, params: dict[str, Any]) -> None:
        self._params = dict(params)

    def set_input(self, name: str, value: Any) -> None:
        if name not in self.inputs:
            raise KeyError(f"{self.name}: unknown input {name}")
        self._input_values[name] = value

    def get_input(self, name: str) -> Any:
        return self._input_values.get(name)

    def get_output(self, name: str) -> Any:
        if name not in self.outputs:
            raise KeyError(f"{self.name}: unknown output {name}")
        return self._output_values[name]

    def set_output(self, name: str, value: Any) -> None:
        if name not in self.outputs:
            raise KeyError(f"{self.name}: unknown output {name}")
        self._output_values[name] = value

    @abstractmethod
    def cycle(self) -> None:
        raise NotImplementedError


REGISTRY: dict[str, type[Block]] = {}
