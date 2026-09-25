"""What the fly's eye sees of the small spike under each Q-05 option. No brain run; writes results/q05_geometry.json and results/q05.html."""

import datetime as dt
import json
from pathlib import Path

import numpy as np

import flydash.fly as fly
from flydash.fly import BIO_MS_PER_FRAME, FRAME_STEPS, FROZEN, obstacle_view, population_rates
from flydash.level import Box, Level, load_cube_section
from flydash.physics import HALF, CubeSim
from flybrain.transducer.looming import LoomingParams

level = load_cube_section(1)
small_vis = next(v for v in level.visuals if v.left == 960.0)
small_box = next(b for b in level.boxes if b.left == 972.0)
tall_vis = next(v for v in level.visuals if v.left == 510.0)
tall_box = next(b for b in level.boxes if b.left == 522.0)
DISTANCES = np.arange(300.0, 0.0, -2.0)  # eye to the spike's left edge, level units


def curve(visual: Box, eye_y: float, gain: float = FROZEN.gain_hz, slow: float = 1.0) -> list[dict]:
    fly.EYE = (10.0, eye_y)
    sim = CubeSim(Level([], end_x=1e9, visuals=[visual]))
    params = LoomingParams(version=FROZEN.version, gain_hz=gain)
    rows = []
    for d in DISTANCES:
        sim.cube.x = visual.left - 10.0 - d
        v = obstacle_view(sim, BIO_MS_PER_FRAME * slow)
        r4, r2 = population_rates(v.theta_deg, v.theta_dot_deg_s, params)
        rows.append({"d": float(d), "theta": round(v.theta_deg, 3), "theta_dot": round(v.theta_dot_deg_s, 1),
                     "lc4": round(float(r4), 4), "lplc2": round(float(r2), 4)})
    fly.EYE = (10.0, 8.0)
    return rows


def jump_window(box: Box) -> list[float]:
    """Eye-to-visual distances at which one tap clears this hazard, on a flat floor."""
    ok = []
    for x0 in np.arange(box.left - 250.0, box.left, 1.0):
        sim = CubeSim(Level([box], end_x=box.right + 200.0))
        sim.cube.x = float(x0)
        sim.step(True)
        while not (sim.cube.dead or sim.cleared or sim.cube.x > box.right + 30):
            sim.step(False)
        if not sim.cube.dead:
            ok.append(float(x0))
    return ok


def as_view_distance(xs: list[float], visual: Box) -> dict:
    d = [visual.left - 10.0 - x for x in xs]
    return {"far": max(d), "near": min(d), "n": len(d)} if d else {}


eyes = {"top_of_face": 8.0, "centre": 0.0, "low": -8.0, "floor": -HALF + 1.0}
out = {
    "experiment": "q05_geometry",
    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "cube_centre_y_on_floor": HALF,
    "closing_speed_units_per_frame": fly.X_SPEED * fly.DT * FRAME_STEPS,
    "small_spike": {"visual": vars(small_vis), "hitbox": vars(small_box)},
    "tall_spike": {"visual": vars(tall_vis), "hitbox": vars(tall_box)},
    "eyes": eyes,
    "curves": {
        "tall_current": curve(tall_vis, 8.0),
        **{f"small_eye_{k}": curve(small_vis, y) for k, y in eyes.items()},
        "small_gain_x3": curve(small_vis, 8.0, gain=3 * FROZEN.gain_hz),
        "small_slow_x2": curve(small_vis, 8.0, slow=2.0),
    },
    "jump_window": {
        "small": as_view_distance(jump_window(small_box), small_vis),
        "tall": as_view_distance(jump_window(tall_box), tall_vis),
    },
    "level_hazard_heights": {},
}
heights = [round(v.top - v.bottom, 1) for v in level.visuals if v.kind == "hazard"]
out["level_hazard_heights"] = {str(h): heights.count(h) for h in sorted(set(heights))}

# Drive at the frame the Giant Fiber first fired on seed 1000 (tall spike). One seed, a rough guide only.
play_now = json.loads(Path("results/fly_play.json").read_text())
first = next(r for r in play_now["attempts"][0]["trace"] if r["gf"])
ref = first["lc4_hz"] + first["lplc2_hz"]
out["gf_reference"] = {"seed": play_now["attempts"][0]["noise_seed"], "cube_x": first["x"], "drive": ref,
                       "d": tall_vis.left - first["x"] - fly.EYE[0]}
drive = {k: [(r["d"], r["lc4"] + r["lplc2"]) for r in rows] for k, rows in out["curves"].items()}
out["summary"] = {
    "peak": {k: max(v for _, v in rows) for k, rows in drive.items()},
    "stops_expanding": {k: min(r["d"] for r in rows if r["theta_dot"] > 0) for k, rows in out["curves"].items()},
    "tall3_cross_ref": max((d for d, v in drive["tall_current"] if 3 * v >= ref), default=None),
}
before = json.loads(Path("results/fly_play_before_F02.json").read_text())["summary"]
now = play_now["summary"]
out["rerun_note"] = (
    f"Rerun after the fix, same 32 seeds: mean progress {100 * now['progress_mean']:.1f}% "
    f"(was {100 * before['progress_mean']:.1f}%), best {100 * now['progress_max']:.1f}% "
    f"(was {100 * before['progress_max']:.1f}%), {now['jumps_mean']:.2f} jumps per attempt (was {before['jumps_mean']:.2f})."
)
Path("results/q05_geometry.json").write_text(json.dumps(out, indent=1))
page = Path("scripts/q05_template.html").read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(out))
Path("results/q05.html").write_text(page, encoding="utf-8")
print(out["gf_reference"], out["summary"], out["rerun_note"], sep="\n")
for k, rows in out["curves"].items():
    peak = max(rows, key=lambda r: r["lc4"] + r["lplc2"])
    last = next((r["d"] for r in reversed(rows) if r["theta_dot"] > 0), None)
    print(f"{k:24s} peak drive {peak['lc4'] + peak['lplc2']:.2f} Hz at d={peak['d']:.0f}, expanding until d={last}")
print("jump windows", out["jump_window"])
print("hazard heights", out["level_hazard_heights"])
