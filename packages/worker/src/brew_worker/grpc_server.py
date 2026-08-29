from __future__ import annotations

import json
import time
from concurrent import futures
from typing import Any

import grpc

from brew_worker.gen import worker_pb2, worker_pb2_grpc
from brew_worker.runtime.engine import Engine
from brew_worker.runtime.graph import ProgramValidationError


def _parse_json_value(raw: str) -> Any:
    return json.loads(raw)


class WorkerServicer(worker_pb2_grpc.WorkerServicer):
    def __init__(self, engine: Engine):
        self._engine = engine

    def DeployProgram(self, request, context):
        try:
            program = json.loads(request.json_program)
            self._engine.deploy(program)
        except (json.JSONDecodeError, ProgramValidationError, KeyError, TypeError, ValueError) as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        status = self._engine.status()
        return worker_pb2.DeployProgramResponse(program_id=status["program_id"] or "")

    def GetProgram(self, request, context):
        status = self._engine.status()
        prog = self._engine._program_dict
        return worker_pb2.GetProgramResponse(
            program_id=status["program_id"] or "",
            json_program=json.dumps(prog) if prog else "",
        )

    def Start(self, request, context):
        try:
            self._engine.start()
        except RuntimeError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        return worker_pb2.StartResponse()

    def Stop(self, request, context):
        self._engine.stop()
        return worker_pb2.StopResponse()

    def SetPort(self, request, context):
        try:
            value = _parse_json_value(request.json_value)
            self._engine.set_master_port(request.name, value)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        return worker_pb2.SetPortResponse()

    def SetParam(self, request, context):
        try:
            value = _parse_json_value(request.json_value)
            with self._engine._lock:
                block = self._engine._blocks.get(request.block)
                if block is None:
                    raise KeyError(f"unknown block: {request.block}")
                block.apply_params({request.param: value})
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        return worker_pb2.SetParamResponse()

    def GetStatus(self, request, context):
        st = self._engine.status()
        return worker_pb2.Status(
            running=bool(st["running"]),
            program_id=st["program_id"] or "",
            cycle_ms=int(st["cycle_ms"] or 0),
            stale=False,
        )

    def SubscribeTelemetry(self, request, context):
        hz = request.hz if request.hz and request.hz > 0 else 5
        period = 1.0 / hz
        while context.is_active():
            snap = self._engine.snapshot()
            frame = worker_pb2.TelemetryFrame(unix_ms=int(time.time() * 1000))
            for k, v in snap.items():
                frame.values_json[k] = json.dumps(v)
            yield frame
            time.sleep(period)

    def ListHalChannels(self, request, context):
        resp = worker_pb2.ListHalChannelsResponse()
        for ch in self._engine._hal.list_channels():
            resp.channels.append(
                worker_pb2.HalChannelInfo(
                    name=ch.name, direction=ch.direction, dtype=ch.dtype
                )
            )
        return resp

    def SetHalChannel(self, request, context):
        try:
            value = _parse_json_value(request.json_value)
            self._engine.set_hal_channel(request.name, value)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        return worker_pb2.SetHalChannelResponse()


def serve(engine: Engine, host: str = "127.0.0.1", port: int = 50051) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    worker_pb2_grpc.add_WorkerServicer_to_server(WorkerServicer(engine), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    return server
