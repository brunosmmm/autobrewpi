from __future__ import annotations

import json
from typing import Any, Iterator

import grpc

from brew_worker.gen import worker_pb2, worker_pb2_grpc


class WorkerClient:
    def __init__(self, target: str = "127.0.0.1:50051"):
        self._target = target
        self._channel: grpc.Channel | None = None
        self._stub: worker_pb2_grpc.WorkerStub | None = None

    @property
    def connected(self) -> bool:
        return self._stub is not None

    def connect(self) -> None:
        if self._channel is not None:
            return
        self._channel = grpc.insecure_channel(self._target)
        self._stub = worker_pb2_grpc.WorkerStub(self._channel)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
        self._channel = None
        self._stub = None

    def _require(self) -> worker_pb2_grpc.WorkerStub:
        if self._stub is None:
            raise RuntimeError("not connected")
        return self._stub

    def deploy_json(self, program: dict[str, Any]) -> str:
        resp = self._require().DeployProgram(
            worker_pb2.DeployProgramRequest(json_program=json.dumps(program))
        )
        return resp.program_id

    def start(self) -> None:
        self._require().Start(worker_pb2.StartRequest())

    def stop(self) -> None:
        self._require().Stop(worker_pb2.StopRequest())

    def set_port(self, name: str, value: float | bool) -> None:
        self._require().SetPort(
            worker_pb2.SetPortRequest(name=name, json_value=json.dumps(value))
        )

    def set_hal_channel(self, name: str, value: float | bool) -> None:
        self._require().SetHalChannel(
            worker_pb2.SetHalChannelRequest(
                name=name, json_value=json.dumps(value)
            )
        )

    def get_status(self) -> dict[str, Any]:
        st = self._require().GetStatus(worker_pb2.GetStatusRequest())
        return {
            "running": st.running,
            "program_id": st.program_id,
            "cycle_ms": st.cycle_ms,
            "stale": st.stale,
        }

    def telemetry_stream(self, hz: int = 5) -> Iterator[dict[str, Any]]:
        stream = self._require().SubscribeTelemetry(
            worker_pb2.SubscribeTelemetryRequest(hz=hz)
        )
        for frame in stream:
            values = {k: json.loads(v) for k, v in frame.values_json.items()}
            yield {"unix_ms": frame.unix_ms, "values": values}
