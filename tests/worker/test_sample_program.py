import json
from pathlib import Path

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins

ROOT = Path(__file__).resolve().parents[2]


def test_sample_program_deploys():
    register_builtins()
    data = json.loads((ROOT / "programs/hlt-loop-v1.json").read_text())
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    eng = Engine(hal)
    eng.deploy(data)
    assert eng.status()["program_id"] == "hlt-loop-v1"
