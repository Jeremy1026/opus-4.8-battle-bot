import bot
from tests.sim import run_match
from tests.bots import rusher, kiter, dummy


def _state(**kw):
    base = {
        "own_position": {"x": 50.0, "y": 50.0}, "own_hp": 100,
        "opponent_position": {"x": 60.0, "y": 50.0}, "opponent_hp": 100,
        "own_facing": {"dx": 1.0, "dy": 0.0},
        "opponent_facing": {"dx": -1.0, "dy": 0.0},
        "ranged_cooldown_remaining": 0, "ranged_uses_remaining": 5, "tick": 0,
    }
    base.update(kw)
    return base


def test_fires_ranged_when_aimed_and_available():
    act, _ = bot.decide(_state(), {})
    assert act["type"] == "attack_ranged"


def test_melee_when_adjacent_and_aimed_no_ranged():
    s = _state(tick=20, opponent_position={"x": 53.0, "y": 50.0},
               ranged_uses_remaining=0, ranged_cooldown_remaining=0)
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_melee"


def test_rotates_when_off_aim():
    s = _state(tick=20, own_facing={"dx": 0.0, "dy": 1.0})  # facing away
    act, _ = bot.decide(s, {})
    assert act["type"] == "rotate"


def test_defensive_phase_defends_when_adjacent():
    # Early game, opponent in melee range with no free ranged shot available:
    # halve the hit instead of trading melee.
    s = _state(tick=0, opponent_position={"x": 53.0, "y": 50.0},
               ranged_uses_remaining=0)
    act, _ = bot.decide(s, {})
    assert act["type"] == "defend"


def test_defensive_phase_backs_off_when_crowded():
    # Early game, opponent inside the safe band but not adjacent: retreat.
    s = _state(tick=5, opponent_position={"x": 58.0, "y": 50.0},
               own_facing={"dx": 0.0, "dy": 1.0})
    act, _ = bot.decide(s, {})
    assert act["type"] == "move"
    assert act["dx"] < 0  # moving away from opponent (who is to our +x)


def test_defensive_phase_still_takes_free_ranged_shot():
    # Even while defending early, a safe aimed ranged shot is worth taking.
    s = _state(tick=0, opponent_position={"x": 70.0, "y": 50.0})
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_ranged"


def test_switches_to_attack_mode_after_defend_ticks():
    # Past the defensive window, adjacent + aimed should attack, not defend.
    s = _state(tick=20, opponent_position={"x": 53.0, "y": 50.0},
               ranged_uses_remaining=0)
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_melee"


def test_moves_closer_when_out_of_range():
    s = _state(opponent_position={"x": 95.0, "y": 50.0})
    act, _ = bot.decide(s, {})
    assert act["type"] in ("move", "rotate")


def test_beats_dummy():
    assert run_match(bot.decide, dummy.decide)["winner"] == "a"


def test_beats_or_draws_rusher():
    assert run_match(bot.decide, rusher.decide)["winner"] in ("a", "draw")


def test_beats_or_draws_kiter():
    assert run_match(bot.decide, kiter.decide)["winner"] in ("a", "draw")
