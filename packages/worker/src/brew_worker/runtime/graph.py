from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ProgramValidationError(ValueError):
    pass


@dataclass
class BlockSpec:
    name: str
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class WireSpec:
    from_port: str
    to_port: str


@dataclass
class Program:
    id: str
    cycle_ms: int
    blocks: list[BlockSpec]
    wires: list[WireSpec]


def parse_program(data: dict[str, Any]) -> Program:
    try:
        blocks = [
            BlockSpec(
                name=b["name"],
                type=b["type"],
                params=dict(b.get("params") or {}),
            )
            for b in data["blocks"]
        ]
        wires = [
            WireSpec(from_port=w["from"], to_port=w["to"]) for w in data["wires"]
        ]
        return Program(
            id=str(data["id"]),
            cycle_ms=int(data["cycle_ms"]),
            blocks=blocks,
            wires=wires,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ProgramValidationError(f"invalid program: {e}") from e


def _block_name(port: str) -> str | None:
    if port.startswith("hal.") or port.startswith("master."):
        return None
    if "." not in port:
        raise ProgramValidationError(f"malformed port: {port}")
    return port.split(".", 1)[0]


def validate_and_order(
    program: Program,
    known_block_types: set[str],
    hal_names: set[str],
) -> list[str]:
    names = [b.name for b in program.blocks]
    if len(names) != len(set(names)):
        raise ProgramValidationError("duplicate block names")

    by_name = {b.name: b for b in program.blocks}
    for b in program.blocks:
        if b.type not in known_block_types:
            raise ProgramValidationError(f"unknown block type: {b.type}")

    # Validate wire endpoints
    for w in program.wires:
        for endpoint in (w.from_port, w.to_port):
            if endpoint.startswith("hal."):
                if endpoint not in hal_names:
                    raise ProgramValidationError(f"unknown HAL channel: {endpoint}")
            elif endpoint.startswith("master."):
                continue
            else:
                bn = _block_name(endpoint)
                if bn not in by_name:
                    raise ProgramValidationError(f"unknown block in port: {endpoint}")

    # Build block→block edges for topo sort
    indegree = {n: 0 for n in names}
    successors: dict[str, set[str]] = {n: set() for n in names}

    for w in program.wires:
        src = _block_name(w.from_port)
        dst = _block_name(w.to_port)
        if src is None or dst is None:
            continue
        if src == dst:
            continue
        if dst not in successors[src]:
            successors[src].add(dst)
            indegree[dst] += 1

    queue = [n for n in names if indegree[n] == 0]
    order: list[str] = []
    while queue:
        # stable: preserve declaration order among ready nodes
        queue.sort(key=lambda n: names.index(n))
        n = queue.pop(0)
        order.append(n)
        for m in sorted(successors[n], key=lambda x: names.index(x)):
            indegree[m] -= 1
            if indegree[m] == 0:
                queue.append(m)

    if len(order) != len(names):
        raise ProgramValidationError("cyclic wire graph")

    return order
