from __future__ import annotations

from brew_worker.runtime.block import Block


class Hysteresis(Block):
    type_name = "Hysteresis"
    inputs = {
        "SetPoint": "float",
        "HystLevel": "float",
        "HystType": "generic",
        "CurrTemp": "float",
        "Enabled": "bool",
    }
    outputs = {"CtlOut": "bool"}

    def __init__(self, name: str, **params):
        super().__init__(name, **params)
        self._deadzone = False
        self.set_output("CtlOut", False)

    def apply_params(self, params: dict) -> None:
        super().apply_params(params)
        if "hyst_type" in params and self.get_input("HystType") is None:
            self.set_input("HystType", params["hyst_type"])
        if "level" in params and self.get_input("HystLevel") is None:
            self.set_input("HystLevel", float(params["level"]))

    def cycle(self) -> None:
        enabled = self.get_input("Enabled")
        if not enabled:
            self.set_output("CtlOut", False)
            self._deadzone = False
            return

        curr = self.get_input("CurrTemp")
        sp = self.get_input("SetPoint")
        level = self.get_input("HystLevel")
        hyst_type = self.get_input("HystType") or "updown"
        if curr is None or sp is None or level is None:
            return

        curr = float(curr)
        sp = float(sp)
        level = float(level)

        if hyst_type == "down":
            output_enable = curr < sp
            output_restart = curr < (sp - level)
        elif hyst_type == "up":
            output_enable = curr < (sp + level)
            output_restart = curr < sp
        elif hyst_type == "updown":
            output_enable = curr < (sp + level)
            output_restart = curr < (sp - level)
        else:
            return

        on = bool(self.get_output("CtlOut"))
        if output_enable:
            if not self._deadzone:
                on = True
            elif output_restart:
                on = True
                self._deadzone = False
        else:
            if self._deadzone:
                if output_restart:
                    on = True
                    self._deadzone = False
            else:
                on = False
                self._deadzone = True

        self.set_output("CtlOut", on)
