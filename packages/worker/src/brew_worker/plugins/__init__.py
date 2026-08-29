from brew_worker.runtime.block import REGISTRY
from brew_worker.plugins.hysteresis import Hysteresis
from brew_worker.plugins.gpio_out import GpioOut


def register_builtins() -> None:
    REGISTRY[Hysteresis.type_name] = Hysteresis
    REGISTRY[GpioOut.type_name] = GpioOut
