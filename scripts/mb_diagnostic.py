"""Can mushroom body learning reach the jump at all? Writes results/mb_diagnostic.json.

Same seeds as results/fly_play.json. With the Kenyon-cell context drive on, every KC->MBON synapse is set to gain 1
(untouched), 0 and 2: the whole range dino-fly's plasticity rule can reach (g_min, g_max). If gain 0 and gain 2 play
the same attempts as gain 1, learning through the real wiring cannot change a jump. No learning happens here.
"""

import argparse
import datetime as dt
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from flydash.fly import MushroomBody, play
from flydash.level import load_cube_section

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--gains", type=float, nargs="+", default=[1.0, 0.0, 2.0])
args = ap.parse_args()

base = json.loads(Path("results/fly_play.json").read_text(encoding="utf-8"))
seeds = [a["noise_seed"] for a in base["attempts"]]
level = load_cube_section(base["level"]["id"])


def behaviour(a) -> tuple:
    return round(a["progress"], 6), tuple(a.get("jump_xs", ()))


conditions = {"no_context": {"attempts": [{k: a[k] for k in ("noise_seed", "progress", "jumps", "gf_spikes")} for a in base["attempts"]]}}
for g in args.gains:
    t0 = time.time()
    mb = MushroomBody(kc_mbon_gain=g)
    res = [a.to_json() for a in play(level, seeds, mb=mb)]
    for a in res:
        a.pop("trace")
    conditions[f"gain_{g:g}"] = {"mushroom_body": asdict(mb), "wall_seconds": round(time.time() - t0, 1), "attempts": res}
    prog = np.array([a["progress"] for a in res])
    print(f"gain {g:g}: mean progress {100 * prog.mean():.1f}%, jumps {np.mean([a['jumps'] for a in res]):.2f}, "
          f"KC spikes/frame {np.mean([a['kc_spikes'] / max(a['frames'], 1) for a in res]):.1f} "
          f"(max {max(a['kc_max_per_frame'] for a in res)}), MBON spikes/frame {np.mean([a['mbon_spikes'] / max(a['frames'], 1) for a in res]):.2f}, "
          f"{time.time() - t0:.0f} s", flush=True)

ref = conditions.get("gain_1")
summary = {}
for name, c in conditions.items():
    prog = [a["progress"] for a in c["attempts"]]
    row = {"progress_mean": float(np.mean(prog)), "jumps_mean": float(np.mean([a["jumps"] for a in c["attempts"]]))}
    if ref is not None:
        row["progress_differs_from_gain_1"] = sum(round(a["progress"], 6) != round(r["progress"], 6) for a, r in zip(c["attempts"], ref["attempts"]))
        if name != "no_context":
            row["behaviour_differs_from_gain_1"] = sum(behaviour(a) != behaviour(r) for a, r in zip(c["attempts"], ref["attempts"]))
    summary[name] = row
out = {"experiment": "mb_diagnostic", "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
       "seeds": seeds, "summary": summary, "conditions": conditions}
Path("results/mb_diagnostic.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(summary, indent=1))
