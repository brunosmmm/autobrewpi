from brew_worker.plugins.hysteresis import Hysteresis


def test_hysteresis_updown_turns_on_below_setpoint():
    h = Hysteresis(name="Hyst")
    h.apply_params({"hyst_type": "updown", "level": 2.0})
    h.set_input("Enabled", True)
    h.set_input("SetPoint", 66.0)
    h.set_input("HystLevel", 2.0)
    h.set_input("HystType", "updown")
    h.set_input("CurrTemp", 60.0)
    h.cycle()
    assert h.get_output("CtlOut") is True
    h.set_input("CurrTemp", 69.0)
    h.cycle()
    assert h.get_output("CtlOut") is False
