from __future__ import annotations

import argparse

import uvicorn

from brew_master.api import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Brew master (operator UI + API)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--worker", default="127.0.0.1:50051")
    args = parser.parse_args(argv)

    app = create_app(worker_target=args.worker)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
