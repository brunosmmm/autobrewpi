import json
import time
from pathlib import Path

import grpc

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.runtime.engine import Engine
from brew_worker.plugins import register_builtins
from brew_worker.grpc_server import serve
from brew_worker.gen import worker_pb2, worker_pb2_grpc

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = json.loads((ROOT / "programs/hlt-loop-v1.json").read_text())


def test_deploy_setport_telemetry():
    register_builtins()
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    eng = Engine(hal)
    server = serve(eng, host="127.0.0.1", port=50052)
    try:
        channel = grpc.insecure_channel("127.0.0.1:50052")
        stub = worker_pb2_grpc.WorkerStub(channel)
        stub.DeployProgram(
            worker_pb2.DeployProgramRequest(json_program=json.dumps(PROGRAM))
        )
        stub.SetHalChannel(
            worker_pb2.SetHalChannelRequest(
                name="hal.adc.temp_c", json_value="50.0"
            )
        )
        stub.SetPort(
            worker_pb2.SetPortRequest(
                name="master.Hyst.SetPoint", json_value="66.0"
            )
        )
        stub.SetPort(
            worker_pb2.SetPortRequest(
                name="master.Hyst.Enabled", json_value="true"
            )
        )
        stub.Start(worker_pb2.StartRequest())
        time.sleep(0.25)
        status = stub.GetStatus(worker_pb2.GetStatusRequest())
        assert status.running is True
        assert status.program_id == "hlt-loop-v1"
        assert hal.get("hal.gpio.heater_hlt") is True
        channel.close()
    finally:
        server.stop(grace=0)
