from tests.sim import run_match
from tests.bots import rusher, dummy


def test_dummy_vs_dummy_is_draw():
    r = run_match(dummy.decide, dummy.decide, max_ticks=50)
    assert r["winner"] == "draw"


def test_rusher_beats_dummy():
    r = run_match(rusher.decide, dummy.decide)
    assert r["winner"] == "a"
