from brew_worker.hal.mock import MockHal
from brew_worker.hal.base import HalChannel


def test_mock_hal_set_get_and_list():
    hal = MockHal(
        [
            HalChannel("hal.adc.hlt_r", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    hal.set("hal.adc.hlt_r", 110.0)
    assert hal.get("hal.adc.hlt_r") == 110.0
    hal.set("hal.gpio.heater_hlt", True)
    assert hal.get("hal.gpio.heater_hlt") is True
    names = {c.name for c in hal.list_channels()}
    assert names == {"hal.adc.hlt_r", "hal.gpio.heater_hlt"}


def test_mock_hal_unknown_channel_raises():
    hal = MockHal([])
    try:
        hal.get("nope")
        assert False, "expected KeyError"
    except KeyError:
        pass
