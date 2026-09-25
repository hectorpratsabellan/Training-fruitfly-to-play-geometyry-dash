"""The fly plays the cube copy: nearest obstacle -> looming drive on LC4/LPLC2 -> whole brain -> Giant Fiber -> jump.

The looming formula, its frozen gain and the motor rule are dino-fly's, unchanged (flybrain.transducer).
"""

from bisect import bisect_right
from dataclasses import asdict, dataclass, field

import numpy as np
from flybrain.transducer.context import ContextParams, context_neurons, context_rates
from flybrain.transducer.looming import FROZEN, NOTHING_IN_VIEW, LoomingParams, View, population_rates
from flybrain.transducer.motor import JumpMotor, MotorParams

from flydash.level import Box, Level
from flydash.physics import DT, HALF, STEPS_PER_S, X_SPEED, CubeSim

FRAME_STEPS = 4  # physics steps per brain update: 60 Hz, like the game's frames
BIO_MS_PER_FRAME = 1000.0 * FRAME_STEPS / STEPS_PER_S  # fly time = game time
EYE = (10.0, 8.0)  # from the cube's centre: front of the face. Our choice.
VIEW_RANGE = 600.0  # 20 blocks, about the visible screen ahead
MOTOR = MotorParams(hold_frames=1)  # one tap = one jump; holding would re-jump on landing


def stream_key(noise_seed: int) -> int:
    return int(noise_seed) & 0xFFFFFFFFFFFFFFFF


def obstacle_view(sim: CubeSim, bio_ms_per_frame: float = BIO_MS_PER_FRAME) -> View:
    """Angle and expansion rate of the nearest object ahead that overlaps the cube's height band."""
    c, vis = sim.cube, sim.level.visuals
    ex, ey = c.x + EYE[0], c.y + EYE[1]
    i = bisect_right(sim.visual_lefts, ex)
    closing = X_SPEED * DT * FRAME_STEPS * (1000.0 / bio_ms_per_frame)  # level units per second of fly time
    while i < len(vis) and vis[i].left < ex + VIEW_RANGE:
        o = vis[i]
        if o.top > c.y - HALF and o.bottom < c.y + HALF:
            d = o.left - ex
            a, b = o.top - ey, o.bottom - ey
            theta = np.arctan2(a, d) - np.arctan2(b, d)
            dtheta_dd = -a / (d * d + a * a) + b / (d * d + b * b)
            return View(i, d, float(np.degrees(theta)), float(np.degrees(-dtheta_dd * closing)))
        i += 1
    return NOTHING_IN_VIEW


@dataclass(frozen=True)
class MushroomBody:
    """dino-fly's Kenyon-cell context drive (its chosen setting, mb_drive_kc.json) and one fixed gain on every KC->MBON synapse."""

    context: ContextParams = ContextParams(code="class_only", rate_hz=40.0, ramp_deg=0.0, min_kc_fraction=0.05, level="kc")
    kc_mbon_gain: float = 1.0


def obstacle_class(o: Box) -> int:
    """The three context classes: 0 full-height hazard, 1 low hazard, 2 block."""
    if o.kind != "hazard":
        return 2
    return 0 if o.top - o.bottom >= 20.0 else 1


def _context_neurons(conn, kc: np.ndarray, lc4: np.ndarray, lplc2: np.ndarray, params: ContextParams) -> np.ndarray:
    """Same selection as dino-fly experiments/mb_drive.py."""
    import pandas as pd
    from flybrain import data_manifest

    ann = pd.read_csv(data_manifest.ensure("flywire_annotations", log=lambda _m: None), sep="	",
                      dtype={"root_id": "Int64"}, usecols=["root_id", "super_class"], low_memory=False)
    ids = ann.loc[ann["super_class"] == "visual_projection", "root_id"].astype("int64").to_numpy()
    vpn = np.setdiff1d(conn.index_of(ids[np.isin(ids, conn.root_ids)]), np.concatenate([lc4, lplc2]))
    return context_neurons(conn, vpn, kc, params)


@dataclass
class Attempt:
    noise_seed: int
    progress: float = 0.0
    cleared: bool = False
    killed_by: str = ""
    frames: int = 0
    jumps: int = 0
    gf_spikes: int = 0
    jump_xs: list[float] = field(default_factory=list)
    kc_spikes: int = 0
    mbon_spikes: int = 0
    kc_max_per_frame: int = 0
    trace: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


def play(
    level: Level,
    noise_seeds: list[int],
    *,
    device: str = "cuda",
    looming: LoomingParams = FROZEN,
    record: bool = False,
    mb: MushroomBody | None = None,
) -> list[Attempt]:
    """One attempt per noise seed, all in parallel as columns of one batched brain."""
    from flybrain import neurons
    from flybrain.connectome import load_connectome
    from flybrain.lif import LIFNetwork, LIFParams, PoissonDrive

    conn = load_connectome("flywire783")
    lc4, lplc2, gf = (neurons.indices(conn, n) for n in ("LC4", "LPLC2", "GF"))
    p = LIFParams()
    b = len(noise_seeds)
    net = LIFNetwork(conn, p, batch_size=b, device=device, chunk_steps=10)
    ctx = kc = mbon = np.zeros(0, dtype=np.int64)
    if mb is not None:
        kc, mbon = neurons.indices(conn, "KC"), neurons.indices(conn, "MBON")
        ctx = _context_neurons(conn, kc, lc4, lplc2, mb.context)
    drive = PoissonDrive(np.concatenate([lc4, lplc2, ctx]), b, p.dt_ms, device=device)
    net.set_drive(drive)
    if mb is not None:
        net.set_plastic(conn.edge_mask(pre_idx=kc, post_idx=mbon)).fill_(mb.kc_mbon_gain)
    net.reset()
    drive.set_seeds(np.array([stream_key(s) for s in noise_seeds], dtype=np.uint64))  # per-neuron streams: extra drive leaves LC4/LPLC2 noise unchanged
    watch = np.concatenate([gf, lc4, lplc2, kc, mbon])
    n_gf, n_lc4, n_lplc2, n_kc = len(gf), len(lc4), len(lplc2), len(kc)
    ctx_rate = np.zeros((len(ctx), b))
    lif_steps = round(BIO_MS_PER_FRAME / p.dt_ms)

    sims = [CubeSim(level) for _ in range(b)]
    motors = [JumpMotor(MOTOR) for _ in range(b)]
    attempts = [Attempt(s) for s in noise_seeds]
    live = np.ones(b, dtype=bool)
    lc4_rate, lplc2_rate = np.zeros(b), np.zeros(b)

    while live.any():
        views = [obstacle_view(s) if live[k] else NOTHING_IN_VIEW for k, s in enumerate(sims)]
        for k, v in enumerate(views):
            r4, r2 = population_rates(v.theta_deg, v.theta_dot_deg_s, looming) if live[k] else (0.0, 0.0)
            lc4_rate[k], lplc2_rate[k] = float(r4), float(r2)
            if mb is not None:
                cls = obstacle_class(sims[k].level.visuals[v.obstacle_index]) if live[k] and v.obstacle_index >= 0 else None
                ctx_rate[:, k] = context_rates(len(ctx), cls, v.theta_deg, mb.context)
        drive.set_rates(
            np.concatenate([np.tile(lc4_rate, (len(lc4), 1)), np.tile(lplc2_rate, (len(lplc2), 1)), ctx_rate])
        )
        res = net.run(lif_steps, record="counts" if record else None, watch=watch)
        wc = res.watch_counts
        gf_n = wc[:n_gf].sum(0)
        totals = res.counts.sum(0) if record else None

        for k in np.flatnonzero(live):
            sim, a, c = sims[k], attempts[k], sims[k].cube
            pressed = motors[k].update(int(gf_n[k]), airborne=not c.on_ground)
            if pressed and c.on_ground:
                a.jumps += 1
                a.jump_xs.append(round(c.x, 2))
            a.gf_spikes += int(gf_n[k])
            if mb is not None:
                kc_n = int(wc[n_gf + n_lc4 + n_lplc2 : n_gf + n_lc4 + n_lplc2 + n_kc, k].sum())
                a.kc_spikes += kc_n
                a.kc_max_per_frame = max(a.kc_max_per_frame, kc_n)
                a.mbon_spikes += int(wc[n_gf + n_lc4 + n_lplc2 + n_kc :, k].sum())
            if record:
                v = views[k]
                a.trace.append(
                    {
                        "x": round(c.x, 2),
                        "y": round(c.y, 2),
                        "theta": round(v.theta_deg, 2),
                        "lc4_hz": round(lc4_rate[k], 3),
                        "lplc2_hz": round(lplc2_rate[k], 3),
                        "gf": int(gf_n[k]),
                        "lc4_spk": int(wc[n_gf : n_gf + n_lc4, k].sum()),
                        "lplc2_spk": int(wc[n_gf + n_lc4 : n_gf + n_lc4 + n_lplc2, k].sum()),
                        "brain_spk": int(totals[k]),
                        "jump": pressed,
                    }
                )
            for _ in range(FRAME_STEPS):
                sim.step(pressed)
            a.frames += 1
            if c.dead or sim.cleared:
                a.progress, a.cleared, a.killed_by = sim.progress, sim.cleared, c.killed_by
                live[k] = False
                net.reset(columns=np.array([k]))  # a finished column must go silent
    return attempts
