"""Local reimplementation of the documented arena mechanics for validation.

Not part of the submitted bot. See battlellmrobots.com/documentation.md.
"""
import copy
import math

MELEE_R, MELEE_D = 5.0, 10
RANGED_R, RANGED_D, RANGED_CD = 30.0, 15, 10
CONE = 0.9239  # cos(22.5 deg)
MAX_ERRORS = 10


def _norm(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (1.0, 0.0)


def _aimed(fx, fy, tx, ty):
    d = math.hypot(tx, ty)
    if d == 0:
        return True
    return (fx * tx + fy * ty) / d >= CONE


def _facing_away(fx, fy, tx, ty):
    """True when the attacker sits within the +/-22.5 cone directly BEHIND us —
    the condition under which `defend` actually reduces damage."""
    d = math.hypot(tx, ty)
    if d == 0:
        return False
    return (fx * tx + fy * ty) / d <= -CONE


def run_match(decide_a, decide_b, max_ticks=500):
    bots = {
        "a": {"pos": [25.0, 50.0], "hp": 100, "face": [1.0, 0.0],
              "cd": 0, "uses": 5, "mem": {}, "errors": 0, "defending": False},
        "b": {"pos": [75.0, 50.0], "hp": 100, "face": [-1.0, 0.0],
              "cd": 0, "uses": 5, "mem": {}, "errors": 0, "defending": False},
    }
    fns = {"a": decide_a, "b": decide_b}
    tick = 0
    for tick in range(max_ticks):
        actions = {}
        for me, other in (("a", "b"), ("b", "a")):
            s = _state(bots[me], bots[other], tick)
            try:
                act, mem = fns[me](copy.deepcopy(s), bots[me]["mem"])
                bots[me]["mem"] = mem if isinstance(mem, dict) else {}
                actions[me] = act if isinstance(act, dict) else {"type": "idle"}
            except Exception:
                bots[me]["errors"] += 1
                actions[me] = {"type": "idle"}
                if bots[me]["errors"] >= MAX_ERRORS:
                    return {"winner": other, "hp_a": bots["a"]["hp"],
                            "hp_b": bots["b"]["hp"], "ticks": tick}
        for me, other in (("a", "b"), ("b", "a")):
            # defend only reduces damage if facing AWAY from the attacker, i.e.
            # the attacker is within the +/-22.5 cone behind us (per platform docs).
            if actions[me].get("type") == "defend":
                m, o = bots[me], bots[other]
                tx, ty = o["pos"][0] - m["pos"][0], o["pos"][1] - m["pos"][1]
                bots[me]["defending"] = _facing_away(m["face"][0], m["face"][1], tx, ty)
            else:
                bots[me]["defending"] = False
            if bots[me]["cd"] > 0:
                bots[me]["cd"] -= 1
        for me, other in (("a", "b"), ("b", "a")):
            _apply(bots[me], bots[other], actions[me])
        if bots["a"]["hp"] <= 0 or bots["b"]["hp"] <= 0:
            break
    return _result(bots, tick)


def _state(m, o, tick):
    return {
        "own_position": {"x": m["pos"][0], "y": m["pos"][1]},
        "own_hp": m["hp"],
        "opponent_position": {"x": o["pos"][0], "y": o["pos"][1]},
        "opponent_hp": o["hp"],
        "own_facing": {"dx": m["face"][0], "dy": m["face"][1]},
        "opponent_facing": {"dx": o["face"][0], "dy": o["face"][1]},
        "ranged_cooldown_remaining": m["cd"],
        "ranged_uses_remaining": m["uses"],
        "tick": tick,
    }


def _damage(defender, dmg):
    defender["hp"] -= dmg * 0.5 if defender["defending"] else dmg


def _apply(m, o, act):
    t = act.get("type")
    if t == "move":
        fx, fy = _norm(act.get("dx", 0), act.get("dy", 0))
        dist = math.hypot(act.get("dx", 0), act.get("dy", 0))
        step = min(dist, 5.0)
        nx = min(100.0, max(0.0, m["pos"][0] + fx * step))
        ny = min(100.0, max(0.0, m["pos"][1] + fy * step))
        if math.hypot(nx - o["pos"][0], ny - o["pos"][1]) >= 4.0:  # 2 * radius
            m["pos"][0], m["pos"][1] = nx, ny
    elif t == "rotate":
        _rotate(m, act.get("dx", 0), act.get("dy", 0))
    elif t == "attack_melee":
        dx, dy = o["pos"][0] - m["pos"][0], o["pos"][1] - m["pos"][1]
        if math.hypot(dx, dy) <= MELEE_R and _aimed(m["face"][0], m["face"][1], dx, dy):
            _damage(o, MELEE_D)
    elif t == "attack_ranged":
        dx, dy = o["pos"][0] - m["pos"][0], o["pos"][1] - m["pos"][1]
        if m["cd"] == 0 and m["uses"] > 0 and math.hypot(dx, dy) <= RANGED_R \
                and _aimed(m["face"][0], m["face"][1], dx, dy):
            _damage(o, RANGED_D)
            m["cd"] = RANGED_CD
            m["uses"] -= 1


def _rotate(m, dx, dy):
    tx, ty = _norm(dx, dy)
    cur = math.atan2(m["face"][1], m["face"][0])
    tgt = math.atan2(ty, tx)
    diff = (tgt - cur + math.pi) % (2 * math.pi) - math.pi
    lim = math.radians(90)
    diff = max(-lim, min(lim, diff))
    ang = cur + diff
    m["face"][0], m["face"][1] = math.cos(ang), math.sin(ang)


def _result(bots, tick):
    a, b = bots["a"]["hp"], bots["b"]["hp"]
    if a <= 0 and b > 0:
        winner = "b"
    elif b <= 0 and a > 0:
        winner = "a"
    elif a > b:
        winner = "a"
    elif b > a:
        winner = "b"
    else:
        winner = "draw"
    return {"winner": winner, "hp_a": a, "hp_b": b, "ticks": tick}
