import math

CONE = 0.9239          # cos(22.5 deg) — attack cone half-angle
MELEE_R = 5.0
RANGED_R = 30.0


def _unit(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (1.0, 0.0)


def decide(state, memory):
    ox = state["opponent_position"]["x"] - state["own_position"]["x"]
    oy = state["opponent_position"]["y"] - state["own_position"]["y"]
    dist = math.hypot(ox, oy)
    fx, fy = state["own_facing"]["dx"], state["own_facing"]["dy"]
    fl = math.hypot(fx, fy) or 1.0
    aim = (fx * ox + fy * oy) / (fl * dist) if dist else 1.0
    aimed = aim >= CONE

    hp = state["own_hp"]
    opp_hp = state["opponent_hp"]
    cd = state["ranged_cooldown_remaining"]
    uses = state["ranged_uses_remaining"]

    prev_hp = memory.get("hp", hp)
    took_damage = hp < prev_hp
    new_mem = {
        "hp": hp,
        "opp": [state["opponent_position"]["x"], state["opponent_position"]["y"]],
    }

    # 1. Ranged: best damage per hit; use whenever aimed and in range.
    if uses > 0 and cd == 0 and dist <= RANGED_R:
        if aimed:
            return {"type": "attack_ranged"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 2. Melee when adjacent.
    if dist <= MELEE_R:
        if aimed:
            return {"type": "attack_melee"}, new_mem
        # Off-aim and adjacent: if we're being hit and not winning, defend.
        if took_damage and hp <= opp_hp:
            return {"type": "defend"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 3. Close distance. Rotate first if badly off-aim so we can act next tick.
    if not aimed:
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Aim for the melee band; move directly toward the opponent.
    ux, uy = _unit(ox, oy)
    step = min(dist - MELEE_R + 1.0, 5.0)
    return {"type": "move", "dx": ux * step, "dy": uy * step}, new_mem
