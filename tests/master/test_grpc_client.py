import json
import time
from pathlib import Path

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins
from brew_worker.grpc_server import serve
from brew_master.grpc_client import WorkerClient

ROOT = Path(__file__).resolve().parents[2]


def test_client_deploy_and_status():
    register_builtins()
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    eng = Engine(hal)
    server = serve(eng, "127.0.0.1", 50053)
    try:
        client = WorkerClient("127.0.0.1:50053")
        client.connect()
        pid = client.deploy_json(
            json.loads((ROOT / "programs/hlt-loop-v1.json").read_text())
        )
        assert pid == "hlt-loop-v1"
        client.set_hal_channel("hal.adc.temp_c", 50.0)
        client.set_port("master.Hyst.SetPoint", 66.0)
        client.set_port("master.Hyst.Enabled", True)
        client.start()
        time.sleep(0.2)
        st = client.get_status()
        assert st["running"] is True
        assert hal.get("hal.gpio.heater_hlt") is True
        client.close()
    finally:
        server.stop(0)
