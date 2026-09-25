"""Turn results/fly_play.json into a self-contained replay page, results/replay.html."""

import json
from pathlib import Path

from flydash.level import load_cube_section
from flydash.physics import CubeSim

FIELDS = ("x", "y", "theta", "lc4_hz", "lplc2_hz", "gf", "lc4_spk", "lplc2_spk", "brain_spk", "jump")

run = json.loads(Path("results/fly_play.json").read_text(encoding="utf-8"))
never = CubeSim(load_cube_section(run["level"]["id"]))
while not never.cube.dead and not never.cleared:
    never.step(False)

traces = []
for a in run["attempts"]:
    if a["trace"]:
        t = {k: [f[k] for f in a["trace"]] for k in FIELDS}
        t["jump"] = [int(v) for v in t["jump"]]
        traces.append({"seed": a["noise_seed"], "progress": a["progress"], "cleared": a["cleared"], **t})
traces.sort(key=lambda t: -t["progress"])

data = {
    "summary": run["summary"],
    "never_jump": never.progress,
    "end_x": run["level"]["end_x"],
    "visuals": run["level"]["visuals"],
    "all_progress": [a["progress"] for a in run["attempts"]],
    "traces": traces,
}
page = Path(__file__).with_name("replay_template.html").read_text(encoding="utf-8")
out = Path("results/replay.html")
out.write_text(page.replace("__DATA__", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(traces)} traces)")
