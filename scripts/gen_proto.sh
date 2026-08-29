#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/packages/worker/src/brew_worker/gen"
mkdir -p "$OUT"
uv run python -m grpc_tools.protoc \
  -I "$ROOT/proto" \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  "$ROOT/proto/worker/v1/worker.proto"

OUT="$OUT" uv run python - <<'PY'
import os
from pathlib import Path

out = Path(os.environ["OUT"])
p = out / "worker/v1/worker_pb2_grpc.py"
text = p.read_text()
text = text.replace(
    "from worker.v1 import worker_pb2 as worker_dot_v1_dot_worker__pb2",
    "from brew_worker.gen.worker.v1 import worker_pb2 as worker_dot_v1_dot_worker__pb2",
)
text = text.replace(
    "import worker_pb2 as ",
    "from brew_worker.gen.worker.v1 import worker_pb2 as ",
)
p.write_text(text)
(out / "__init__.py").write_text(
    "from brew_worker.gen.worker.v1 import worker_pb2, worker_pb2_grpc\n\n"
    '__all__ = ["worker_pb2", "worker_pb2_grpc"]\n'
)
(out / "worker/__init__.py").write_text("")
(out / "worker/v1/__init__.py").write_text("")
print(f"generated into {out}")
PY
