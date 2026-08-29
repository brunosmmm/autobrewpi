import pytest
from brew_worker.runtime.graph import (
    parse_program,
    validate_and_order,
    ProgramValidationError,
)

SAMPLE = {
    "id": "t1",
    "cycle_ms": 100,
    "blocks": [
        {"name": "A", "type": "Hysteresis", "params": {}},
        {"name": "B", "type": "GpioOut", "params": {"channel": "hal.gpio.heater_hlt"}},
    ],
    "wires": [
        {"from": "hal.adc.hlt_r", "to": "A.CurrTemp"},
        {"from": "master.SetPoint", "to": "A.SetPoint"},
        {"from": "A.CtlOut", "to": "B.Value"},
    ],
}


def test_parse_and_topo_ok():
    prog = parse_program(SAMPLE)
    order = validate_and_order(
        prog,
        known_block_types={"Hysteresis", "GpioOut"},
        hal_names={"hal.adc.hlt_r", "hal.gpio.heater_hlt"},
    )
    assert order.index("A") < order.index("B")


def test_rejects_cycle():
    data = {
        "id": "cyc",
        "cycle_ms": 50,
        "blocks": [
            {"name": "A", "type": "Hysteresis", "params": {}},
            {"name": "B", "type": "Hysteresis", "params": {}},
        ],
        "wires": [
            {"from": "A.CtlOut", "to": "B.CurrTemp"},
            {"from": "B.CtlOut", "to": "A.CurrTemp"},
        ],
    }
    prog = parse_program(data)
    with pytest.raises(ProgramValidationError):
        validate_and_order(prog, {"Hysteresis"}, set())
