"""Search for any hold/release sequence that clears the cube section. If none exists, the copy is wrong."""

import copy
import sys

from flydash.level import load_cube_section
from flydash.physics import CubeSim


def solve(level_id: int = 1) -> list[bool] | None:
    start = CubeSim(load_cube_section(level_id))
    frontier: list[tuple[CubeSim, list[bool]]] = [(start, [])]
    while frontier:
        nxt, seen = [], set()
        for sim, inputs in frontier:
            for hold in (False, True):
                s = copy.copy(sim)
                s.cube = copy.copy(sim.cube)
                s.step(hold)
                if s.cube.dead:
                    continue
                if s.cleared:
                    return [*inputs, hold]
                key = (round(s.cube.y, 3), round(s.cube.vy, 3), s.cube.on_ground)
                if key not in seen:
                    seen.add(key)
                    nxt.append((s, [*inputs, hold]))
        frontier = nxt
    return None


if __name__ == "__main__":
    inputs = solve(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    if inputs is None:
        print("NOT BEATABLE in the copy")
        sys.exit(1)
    presses = sum(1 for a, b in zip([False, *inputs], inputs, strict=False) if b and not a)
    print(f"beatable: {len(inputs)} steps ({len(inputs) / 240:.2f} s), {presses} presses")
