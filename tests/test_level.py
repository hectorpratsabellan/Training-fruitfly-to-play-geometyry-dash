import pytest

from flydash.level import GD_LEVELS, load_cube_section

pytestmark = pytest.mark.skipif(not (GD_LEVELS / "1.txt").exists(), reason="Geometry Dash not installed")


def test_stereo_madness_cube_section():
    level = load_cube_section(1)
    assert level.end_x == 7995.0
    kinds = [b.kind for b in level.boxes]
    # Counted from the decoded level file on 2026-09-25.
    assert kinds.count("hazard") == 25 + 1 + 90
    assert kinds.count("solid") == 3 + 126 + 12 + 5 + 3 + 13 + 35
