"""Read official Geometry Dash levels from the game's Resources folder into hitboxes."""

import base64
import zlib
from dataclasses import dataclass, field
from pathlib import Path

GD_LEVELS = Path(r"C:\Users\Hector\Games\Steam\steamapps\common\Geometry Dash\Resources\levels")

# Object id -> (kind, width, height), centred on the object's position, in level units (30 = one block).
# UNVERIFIED sizes: community values, to be checked against the game through the Geode mod (Fly Open Questions Q-02).
HITBOXES = {
    **{i: ("solid", 30.0, 30.0) for i in (1, 2, 3, 4, 6, 7)},
    40: ("solid", 30.0, 14.0),  # half slab
    8: ("hazard", 6.0, 12.0),  # spike
    39: ("hazard", 6.0, 5.6),  # small spike
    103: ("hazard", 4.0, 7.6),  # medium spike
    9: ("hazard", 30.0, 9.2),  # floor spike strip
}
# What the fly sees: the drawn shape, not the hitbox. A spike is drawn a full block tall. Heights by eye.
VISUAL_HEIGHT = {40: 15.0, 39: 15.0, 103: 20.0, 9: 12.0}
SHIP_PORTAL = 13


@dataclass(frozen=True)
class Box:
    kind: str
    left: float
    right: float
    bottom: float
    top: float


def decode(path: Path) -> str:
    s = path.read_text().strip()
    return zlib.decompress(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)), 15 | 32).decode()


def parse_objects(level_string: str) -> list[dict[str, str]]:
    objs = []
    for chunk in level_string.split(";")[1:]:
        if chunk:
            parts = chunk.split(",")
            objs.append(dict(zip(parts[::2], parts[1::2], strict=True)))
    return objs


@dataclass(frozen=True)
class Level:
    boxes: list[Box]
    end_x: float
    visuals: list[Box] = field(default_factory=list)


def load_cube_section(level_id: int = 1, levels_dir: Path = GD_LEVELS) -> Level:
    """The level up to its first ship portal. Rotations are ignored: this section only rotates square blocks."""
    objs = parse_objects(decode(levels_dir / f"{level_id}.txt"))
    end_x = min(float(o["2"]) for o in objs if int(o["1"]) == SHIP_PORTAL)
    boxes, visuals = [], []
    for o in objs:
        obj_id, x, y = int(o["1"]), float(o["2"]), float(o.get("3", 0))
        if obj_id in HITBOXES and x < end_x:
            kind, w, h = HITBOXES[obj_id]
            boxes.append(Box(kind, x - w / 2, x + w / 2, y - h / 2, y + h / 2))
            vh = VISUAL_HEIGHT.get(obj_id, 30.0)
            visuals.append(Box(kind, x - 15, x + 15, y - vh / 2, y + vh / 2))
    boxes.sort(key=lambda b: b.left)
    visuals.sort(key=lambda b: b.left)
    return Level(boxes, end_x, visuals)
