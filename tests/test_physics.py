import pytest

from flydash.level import HITBOXES, Box, Level
from flydash.physics import STEPS_PER_S, CubeSim


def spikes(*xs: float) -> Level:
    _, w, h = HITBOXES[8]
    return Level([Box("hazard", x - w / 2, x + w / 2, 15 - h / 2, 15 + h / 2) for x in xs], end_x=1000.0)


def single_jump(sim: CubeSim, jump_step: int, steps: int = 400) -> CubeSim:
    for i in range(steps):
        sim.step(hold=i == jump_step)
    return sim


def test_jump_shape():
    sim = CubeSim(Level([], end_x=1e9))
    sim.step(hold=True)
    top, n = sim.cube.y, 1
    while not sim.cube.on_ground:
        sim.step(hold=False)
        top, n = max(top, sim.cube.y), n + 1
    # 2.13 or 2.22 blocks depending on update order, which is unverified. Fly Issues F-01.
    assert 2.12 <= (top - 15) / 30 <= 2.23
    assert n / STEPS_PER_S == pytest.approx(0.39, abs=0.01)
    assert sim.cube.x / 30 == pytest.approx(4.05, abs=0.1)


def test_triple_spike_is_clearable_and_quadruple_is_not():
    def clearable(n: int) -> bool:
        xs = [300 + 30 * k for k in range(n)]
        return any(not single_jump(CubeSim(spikes(*xs)), j).cube.dead for j in range(250))

    assert clearable(3)
    assert not clearable(4)


def test_running_into_a_wall_kills_and_landing_on_top_does_not():
    wall = Level([Box("solid", 300, 330, 0, 30)], end_x=1000.0)
    assert single_jump(CubeSim(wall), jump_step=-1).cube.dead
    assert any(not single_jump(CubeSim(wall), j).cube.dead for j in range(250))
