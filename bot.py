import math

CONE = 0.9239          # cos(22.5 deg) — attack cone half-angle
MELEE_R = 5.0
RANGED_R = 30.0
DEFEND_TICKS = 20      # open defensively, then switch to attack mode


def _unit(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (1.0, 0.0)


def decide(state, memory):
    # Guard every access: a KeyError here would forfeit the tick on the platform.
    own = state.get("own_position", {})
    opp = state.get("opponent_position", {})
    face = state.get("own_facing", {})
    ox = opp.get("x", 0.0) - own.get("x", 0.0)
    oy = opp.get("y", 0.0) - own.get("y", 0.0)
    dist = math.hypot(ox, oy)
    fx, fy = face.get("dx", 1.0), face.get("dy", 0.0)
    fl = math.hypot(fx, fy) or 1.0
    aim = (fx * ox + fy * oy) / (fl * dist) if dist else 1.0
    aimed = aim >= CONE

    hp = state.get("own_hp", 100)
    opp_hp = state.get("opponent_hp", 100)
    cd = state.get("ranged_cooldown_remaining", 0)
    uses = state.get("ranged_uses_remaining", 0)

    if not isinstance(memory, dict):
        memory = {}
    tick = memory.get("tick", state.get("tick", 0))
    new_mem = {"hp": hp, "tick": tick + 1}

    # Phase 1 (opening): defensive posture. `defend` is near-useless here (it
    # only helps when facing away from the attacker), and equal move speeds mean
    # we can't out-run anyone — so the real defense is to stay at range, keep the
    # opponent aimed, and chip with free ranged shots without diving into melee.
    if tick < DEFEND_TICKS:
        # Free 15-damage ranged shot when aimed and in range — always worth it.
        if aimed and uses > 0 and cd == 0 and dist <= RANGED_R:
            return {"type": "attack_ranged"}, new_mem
        # Forced into melee: fight back rather than get pounded passively.
        if dist <= MELEE_R:
            return ({"type": "attack_melee"} if aimed
                    else {"type": "rotate", "dx": ox, "dy": oy}), new_mem
        # Not aimed: turn toward the opponent so we can fire / track next tick.
        if not aimed:
            return {"type": "rotate", "dx": ox, "dy": oy}, new_mem
        # Out of ranged range: edge in until we can shoot (kite toward open
        # space if the opponent is running, so we don't wall-trap ourselves).
        if dist > RANGED_R:
            ux, uy = _unit(ox, oy)
            step = min(dist - RANGED_R + 1.0, 5.0)
            return {"type": "move", "dx": ux * step, "dy": uy * step}, new_mem
        # In range, aimed, shot on cooldown: keep facing the opponent so the next
        # shot lands the instant the cooldown clears (rotating tracks them for free).
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Phase 2 (attack mode) ------------------------------------------------
    # 1. Ranged: best damage per hit; use whenever aimed and in range.
    if uses > 0 and cd == 0 and dist <= RANGED_R:
        if aimed:
            return {"type": "attack_ranged"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 2. Melee when adjacent.
    if dist <= MELEE_R:
        if aimed:
            return {"type": "attack_melee"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 3. Close distance. Rotate first if badly off-aim so we can act next tick.
    if not aimed:
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Aim for the melee band; move directly toward the opponent.
    ux, uy = _unit(ox, oy)
    step = min(dist - MELEE_R + 1.0, 5.0)
    return {"type": "move", "dx": ux * step, "dy": uy * step}, new_mem
