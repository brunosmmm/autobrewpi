import json
import time
from pathlib import Path

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

ROOT = Path(__file__).resolve().parents[2]


def test_engine_keeps_running_without_grpc():
    register_builtins()
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    eng = Engine(hal)
    eng.deploy(json.loads((ROOT / "programs/hlt-loop-v1.json").read_text()))
    eng.set_hal_channel("hal.adc.temp_c", 50.0)
    eng.set_master_port("master.Hyst.Enabled", True)
    eng.set_master_port("master.Hyst.SetPoint", 66.0)
    eng.start()
    time.sleep(0.15)
    assert eng.status()["running"] is True
    assert hal.get("hal.gpio.heater_hlt") is True
    eng.stop()
