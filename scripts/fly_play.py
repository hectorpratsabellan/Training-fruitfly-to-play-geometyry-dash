"""Run the reflex fly on Stereo Madness's cube section and write results/fly_play.json."""

import argparse
import datetime as dt
import json
import time
from pathlib import Path

import numpy as np

from flydash.fly import BIO_MS_PER_FRAME, EYE, FROZEN, MOTOR, play
from flydash.level import load_cube_section

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--attempts", type=int, default=32)
ap.add_argument("--first-seed", type=int, default=1000)
ap.add_argument("--trace", type=int, nargs="*", default=[1000], help="noise seeds to record in full")
args = ap.parse_args()

level = load_cube_section(1)
seeds = list(range(args.first_seed, args.first_seed + args.attempts))
t0 = time.time()
traced = play(level, [s for s in seeds if s in args.trace], record=True)
rest = play(level, [s for s in seeds if s not in args.trace])
attempts = sorted(traced + rest, key=lambda a: a.noise_seed)
secs = time.time() - t0

prog = np.array([a.progress for a in attempts])
summary = {
    "attempts": len(attempts),
    "progress_mean": float(prog.mean()),
    "progress_median": float(np.median(prog)),
    "progress_max": float(prog.max()),
    "cleared": sum(a.cleared for a in attempts),
    "killed_by": {k: sum(a.killed_by == k for a in attempts) for k in ("hazard", "wall")},
    "jumps_mean": float(np.mean([a.jumps for a in attempts])),
    "gf_spikes_mean": float(np.mean([a.gf_spikes for a in attempts])),
    "wall_seconds": round(secs, 1),
}
out = {
    "experiment": "fly_play",
    "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    "params": {
        "gain_hz": FROZEN.gain_hz,
        "transducer_version": FROZEN.version,
        "bio_ms_per_frame": BIO_MS_PER_FRAME,
        "eye": EYE,
        "hold_frames": MOTOR.hold_frames,
        "seeds": seeds,
    },
    "level": {
        "id": 1,
        "end_x": level.end_x,
        "boxes": [[b.kind, b.left, b.right, b.bottom, b.top] for b in level.boxes],
        "visuals": [[b.kind, b.left, b.right, b.bottom, b.top] for b in level.visuals],
    },
    "summary": summary,
    "attempts": [a.to_json() for a in attempts],
}
path = Path("results") / "fly_play.json"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(out) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
print("per attempt:", " ".join(f"{a.progress:.1%}" for a in attempts))
print(f"wrote {path}")
