from flydash.fly import BIO_MS_PER_FRAME, FRAME_STEPS, obstacle_view
from flydash.level import Box, Level
from flydash.physics import CubeSim


def view_at(visual: Box, x: float):
    sim = CubeSim(Level([], end_x=1e9, visuals=[visual]))
    sim.cube.x = x
    return obstacle_view(sim)


def test_block_tall_spike_looms_while_approaching():
    spike = Box("hazard", 300, 330, 0, 30)
    far, near = view_at(spike, 0), view_at(spike, 250)
    assert 0 < far.theta_deg < near.theta_deg
    assert near.theta_dot_deg_s > far.theta_dot_deg_s > 0


def test_low_small_spike_close_by_is_not_expanding():
    # Entirely below the eye: seen from above, it shrinks in the last few units. Why the fly dies at 12%.
    small = Box("hazard", 300, 330, -1.5, 13.5)
    assert view_at(small, 280).theta_dot_deg_s < 0


def test_objects_outside_the_cubes_height_are_ignored():
    overhead = Box("solid", 300, 330, 60, 90)
    assert view_at(overhead, 200).obstacle_index == -1


def test_expansion_rate_matches_one_frame_of_motion():
    # see Fly Issues F-02: closing speed once missed DT and ran 4x fast
    spike = Box("hazard", 300, 330, 0, 30)
    sim = CubeSim(Level([], end_x=1e9, visuals=[spike]))
    sim.cube.x = 150
    before = obstacle_view(sim)
    for _ in range(FRAME_STEPS):
        sim.step(False)
    after = obstacle_view(sim)
    finite = (after.theta_deg - before.theta_deg) * 1000.0 / BIO_MS_PER_FRAME
    assert abs(before.theta_dot_deg_s / finite - 1) < 0.05
