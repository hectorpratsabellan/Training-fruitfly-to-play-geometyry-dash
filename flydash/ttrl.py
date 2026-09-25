"""ToastyReplay-Lite .ttrl replay files: the fly's presses, played back in the real game.

Format read from ToastexGD/ToastyReplay-Lite src/replay/TtrlCodec.cpp (v1.0.12). We write only what it needs:
240 TPS, normal mode, jump button, player 1, no frame fixes, no seed.
"""

import struct
import zlib
from dataclasses import dataclass

MAGIC, VERSION = b"TTRL", 1
GAME_VERSION = 22081  # 2.2081, the Steam build Geode 5.10.1 supports


@dataclass
class Replay:
    level_id: int
    tick_count: int
    inputs: list[tuple[int, bool]]  # (before_tick, pressed), ascending
    tps: int = 240


def _varint(v: int) -> bytes:
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def encode(r: Replay) -> bytes:
    inputs, prev = bytearray(), 0
    for tick, pressed in r.inputs:
        assert prev <= tick < r.tick_count
        inputs += _varint(((tick - prev) << 1) | int(pressed))
        prev = tick
    body = bytearray(MAGIC) + bytes([VERSION, 0])
    for v in (r.tps, 1, GAME_VERSION, r.level_id, 0):  # tps num, tps den, game version, level id, revision 0 = unchecked
        body += _varint(v)
    body += struct.pack("<Q", 0)  # level fingerprint 0 = unchecked
    body += _varint(r.tick_count) + _varint(len(inputs)) + inputs
    return bytes(body) + struct.pack("<I", zlib.crc32(body))  # same CRC-32 as the mod's checksum()


def decode(data: bytes) -> Replay:
    body, (crc,) = data[:-4], struct.unpack("<I", data[-4:])
    if zlib.crc32(body) != crc or body[:4] != MAGIC or body[4] != VERSION or body[5] != 0:
        raise ValueError("not a plain v1 TTRL file")
    pos = 6

    def varint() -> int:
        nonlocal pos
        v = shift = 0
        while True:
            b = body[pos]
            pos += 1
            v |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                return v

    tps, _den, _gv, level_id, _rev = (varint() for _ in range(5))
    pos += 8
    tick_count, size = varint(), varint()
    end, inputs, tick = pos + size, [], 0
    while pos < end:
        v = varint()
        tick += v >> 1
        inputs.append((tick, bool(v & 1)))
    return Replay(level_id, tick_count, inputs, tps)


def from_trace(trace: list[dict], frame_steps: int, level_id: int, margin_ticks: int = 480) -> Replay:
    """Press on the first tick of every frame the motor pressed, release when it stops. Mirrors fly.play()."""
    inputs, held = [], False
    for k, f in enumerate(trace):
        if f["jump"] != held:
            held = f["jump"]
            inputs.append((k * frame_steps, held))
    if held:
        inputs.append((len(trace) * frame_steps, False))
    return Replay(level_id, len(trace) * frame_steps + margin_ticks, inputs)
