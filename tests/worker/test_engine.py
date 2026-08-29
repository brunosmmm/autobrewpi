import time

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

PROGRAM = {
    "id": "hlt-loop-v1",
    "cycle_ms": 50,
    "blocks": [
        {
            "name": "Hyst",
            "type": "Hysteresis",
            "params": {"hyst_type": "updown", "level": 2.0},
        },
        {
            "name": "HeatOut",
            "type": "GpioOut",
            "params": {"channel": "hal.gpio.heater_hlt"},
        },
    ],
    "wires": [
        {"from": "hal.adc.temp_c", "to": "Hyst.CurrTemp"},
        {"from": "master.Hyst.SetPoint", "to": "Hyst.SetPoint"},
        {"from": "master.Hyst.Enabled", "to": "Hyst.Enabled"},
        {"from": "Hyst.CtlOut", "to": "HeatOut.Value"},
    ],
}


def test_engine_heats_when_cold():
    register_builtins()
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    eng = Engine(hal)
    eng.deploy(PROGRAM)
    eng.set_hal_channel("hal.adc.temp_c", 50.0)
    eng.set_master_port("master.Hyst.SetPoint", 66.0)
    eng.set_master_port("master.Hyst.Enabled", True)
    eng.start()
    time.sleep(0.2)
    eng.stop()
    assert hal.get("hal.gpio.heater_hlt") is True
