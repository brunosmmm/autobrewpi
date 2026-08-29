from __future__ import annotations

import argparse
from pathlib import Path

from brew_worker.hal.base import HalChannel
from brew_worker.hal.mock import MockHal
from brew_worker.plugins import register_builtins
from brew_worker.runtime.engine import Engine
from brew_worker.grpc_server import serve


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Brew worker (mock HAL)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument(
        "--persist",
        type=Path,
        default=Path("state/worker_program.json"),
        help="Path to persist last deployed program",
    )
    args = parser.parse_args(argv)

    register_builtins()
    hal = MockHal(
        [
            HalChannel("hal.adc.temp_c", "input", "float"),
            HalChannel("hal.gpio.heater_hlt", "output", "bool"),
        ]
    )
    engine = Engine(hal, persist_path=args.persist)
    engine.load_persisted()

    server = serve(engine, host=args.host, port=args.port)
    print(f"brew-worker listening on {args.host}:{args.port} (mock HAL)")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
