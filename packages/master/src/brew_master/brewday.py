from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brew_master.supervisor import WorkerSupervisor

ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PROGRAM = ROOT / "programs" / "hlt-loop-v1.json"


class BrewDayController:
    def __init__(self, supervisor: WorkerSupervisor):
        self._sup = supervisor
        self._enabled = False
        self._setpoint_c = 66.0

    def ensure_sample_deployed(self) -> None:
        client = self._sup.client()
        if not client.connected:
            client.connect()
        program = json.loads(SAMPLE_PROGRAM.read_text())
        client.deploy_json(program)
        client.start()

    def set_manual(self, *, enabled: bool, setpoint_c: float) -> None:
        client = self._sup.client()
        if not client.connected:
            client.connect()
        self._enabled = enabled
        self._setpoint_c = float(setpoint_c)
        client.set_port("master.Hyst.SetPoint", self._setpoint_c)
        client.set_port("master.Hyst.Enabled", self._enabled)
        st = client.get_status()
        if not st.get("running"):
            client.start()

    def inject_temp(self, temp_c: float) -> None:
        client = self._sup.client()
        if not client.connected:
            client.connect()
        client.set_hal_channel("hal.adc.temp_c", float(temp_c))

    def state(self) -> dict[str, Any]:
        return {
            "mode": "manual",
            "enabled": self._enabled,
            "setpoint_c": self._setpoint_c,
            "worker": self._sup.snapshot(),
        }
