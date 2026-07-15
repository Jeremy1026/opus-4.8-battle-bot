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
    # Attack mode (past the opening): aimed + shot ready -> fire.
    act, _ = bot.decide(_state(tick=20), {})
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


def test_defensive_phase_melee_counters_when_forced():
    # Early game, opponent in melee range with no ranged shot left: fight back
    # (melee) rather than stand still — `defend` is useless facing the attacker.
    s = _state(tick=5, opponent_position={"x": 53.0, "y": 50.0},
               ranged_uses_remaining=0)
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_melee"


def test_turns_away_from_unanswerable_ranged_threat():
    # Opening, opponent holding range, our ranged spent: turn our back so that
    # `defend` will actually reduce damage next tick.
    s = _state(tick=5, opponent_position={"x": 70.0, "y": 50.0},
               ranged_uses_remaining=0)
    act, _ = bot.decide(s, {"tick": 5, "dist": 20.0})  # not closing
    assert act["type"] == "rotate"
    assert act["dx"] < 0  # turning away from opponent (who is to our +x)


def test_defends_once_facing_away():
    # Same situation, but already facing away -> the defend now actually applies.
    s = _state(tick=5, opponent_position={"x": 70.0, "y": 50.0},
               own_facing={"dx": -1.0, "dy": 0.0}, ranged_uses_remaining=0)
    act, _ = bot.decide(s, {"tick": 5, "dist": 20.0})
    assert act["type"] == "defend"


def test_never_turns_back_on_a_closing_opponent():
    # Opponent charging in (distance shrinking): turning away would let them
    # pound us for free, so we must not turtle.
    s = _state(tick=5, opponent_position={"x": 70.0, "y": 50.0},
               ranged_uses_remaining=0)
    act, _ = bot.decide(s, {"tick": 5, "dist": 30.0})  # closing 30 -> 20
    assert act["type"] != "defend"
    assert not (act["type"] == "rotate" and act["dx"] < 0)


def test_never_defends_in_melee():
    # Facing away from an adjacent melee attacker is suicide — trade instead.
    for mem in ({"tick": 0, "dist": 3.0}, {"tick": 0, "dist": 30.0}):
        s = _state(tick=0, opponent_position={"x": 53.0, "y": 50.0},
                   ranged_uses_remaining=0)
        act, _ = bot.decide(s, mem)
        assert act["type"] != "defend"


def test_defensive_phase_takes_free_ranged_shot_in_range():
    # Aimed, in ranged range, shot ready: take the free chip damage.
    s = _state(tick=0, opponent_position={"x": 70.0, "y": 50.0})
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_ranged"


def test_never_stalls_from_far_start():
    # From a distant start (out of ranged range) the very first action must
    # make progress, not spin in place forever.
    s = _state(tick=0, own_position={"x": 25.0, "y": 50.0},
               opponent_position={"x": 75.0, "y": 50.0})
    act, mem = bot.decide(s, {})
    assert act["type"] in ("move", "rotate", "attack_ranged")
    assert mem["tick"] == 1


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
