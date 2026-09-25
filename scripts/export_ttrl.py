"""Write each traced attempt in results/fly_play.json as a ToastyReplay-Lite macro, results/ttrl/fly seed N.ttrl.

Each file is checked first: its inputs, stepped through the copy tick by tick, must end the attempt where the fly did.
"""

import json
from pathlib import Path

from flydash.fly import FRAME_STEPS
from flydash.level import load_cube_section
from flydash.physics import CubeSim
from flydash.ttrl import decode, encode, from_trace

run = json.loads(Path("results/fly_play.json").read_text(encoding="utf-8"))
level = load_cube_section(run["level"]["id"])
out = Path("results/ttrl")
out.mkdir(exist_ok=True)
for a in (a for a in run["attempts"] if a["trace"]):
    data = encode(from_trace(a["trace"], FRAME_STEPS, level_id=run["level"]["id"]))
    replay = decode(data)
    sim, presses, held = CubeSim(level), dict(replay.inputs), False
    for tick in range(replay.tick_count):
        held = presses.get(tick, held)
        sim.step(held)
        if sim.cube.dead or sim.cleared:
            break
    assert abs(sim.progress - a["progress"]) < 1e-9, (a["noise_seed"], sim.progress, a["progress"])
    path = out / f"fly seed {a['noise_seed']}.ttrl"
    path.write_bytes(data)
    print(f"{path}: {sum(p for _, p in replay.inputs)} presses, copy dies at {100 * a['progress']:.1f}% (x = {sim.cube.x:.0f})")
