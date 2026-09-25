"""Cube mode at normal speed, stepped 240 times per second like Geometry Dash 2.2."""

from bisect import bisect_left
from dataclasses import dataclass

from flydash.level import Level

# From PlayerObject::updateTimeMod and updateJump in github.com/camila314/gdp (speed 0.9 = normal).
# Velocities are per 1/60 s; one 240 Hz step is dt = 0.25 of that.
JUMP_V = 11.1800318
GRAVITY = 0.958199024
MAX_FALL = 15.0
X_SPEED = 0.9 * 5.77000189
DT = 0.25
STEPS_PER_S = 240

HALF = 15.0  # player hitbox is one block
INNER_HALF = 4.5  # 9x9 inner box: touching a solid with it kills


@dataclass
class Cube:
    x: float = 0.0
    y: float = HALF  # centre; the floor is y = 0
    vy: float = 0.0
    on_ground: bool = True
    dead: bool = False
    killed_by: str = ""


class CubeSim:
    def __init__(self, level: Level):
        self.level = level
        self._lefts = [b.left for b in level.boxes]
        self.visual_lefts = [b.left for b in level.visuals]
        self._widest = max((b.right - b.left for b in level.boxes), default=0.0)
        self.cube = Cube()

    @property
    def progress(self) -> float:
        return min(self.cube.x / self.level.end_x, 1.0)

    @property
    def cleared(self) -> bool:
        return self.cube.x >= self.level.end_x

    def nearby(self, x0: float, x1: float):
        i = bisect_left(self._lefts, x0 - self._widest)
        while i < len(self._lefts) and self._lefts[i] <= x1:
            b = self.level.boxes[i]
            if b.right >= x0:
                yield b
            i += 1

    def step(self, hold: bool) -> None:
        """One 240 Hz step. Position update order is ASSUMED (velocity first, then position); verify with Geode."""
        c = self.cube
        if c.dead or self.cleared:
            return
        if c.on_ground and hold:
            c.vy = JUMP_V
        else:
            c.vy = max(c.vy - GRAVITY * DT, -MAX_FALL)
        c.x += X_SPEED * DT
        c.y += c.vy * DT
        c.on_ground = False

        if c.y - HALF <= 0:
            c.y, c.vy, c.on_ground = HALF, 0.0, True

        for b in self.nearby(c.x - HALF, c.x + HALF):
            if c.y + HALF <= b.bottom or c.y - HALF >= b.top:
                continue
            if b.kind == "hazard":
                c.dead, c.killed_by = True, "hazard"
                return
            inner_hits = (
                c.x + INNER_HALF > b.left
                and c.x - INNER_HALF < b.right
                and c.y + INNER_HALF > b.bottom
                and c.y - INNER_HALF < b.top
            )
            if inner_hits:
                c.dead, c.killed_by = True, "wall"
                return
            if c.vy <= 0 and c.y > b.top:
                c.y, c.vy, c.on_ground = b.top + HALF, 0.0, True
