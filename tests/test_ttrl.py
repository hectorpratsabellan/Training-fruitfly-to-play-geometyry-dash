from flydash.ttrl import Replay, decode, encode, from_trace


def test_round_trip():
    r = Replay(1, 5000, [(0, True), (4, False), (1200, True), (1204, False)])
    assert decode(encode(r)) == r


def test_header_bytes():
    # magic, version 1, no flags, 240/1 TPS, game version 22081, level 1, revision 0
    assert encode(Replay(1, 10, []))[:13] == b"TTRL\x01\x00\xf0\x01\x01\xc1\xac\x01\x01"


def test_trace_presses_become_one_frame_holds():
    trace = [{"jump": j} for j in (False, True, False, False, True, True, False)]
    assert from_trace(trace, 4, 1, margin_ticks=0).inputs == [(4, True), (8, False), (16, True), (24, False)]
