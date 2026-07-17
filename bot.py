import math

CONE = 0.9239          # cos(22.5 deg) — attack cone half-angle
MELEE_R = 5.0
RANGED_R = 30.0
DEFEND_TICKS = 20      # open defensively, then switch to attack mode
TURN_BACK_TICKS = 3    # cooldown needed to justify turning away and back (180 deg = 2 ticks)
TURTLE_MIN_R = 10.0    # never turn our back on an opponent closer than this


def _unit(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (1.0, 0.0)


def _melee(ox, oy, aimed, opp_aimed):
    """Melee with a flank-dodge: strike when we're aimed and the opponent is not
    (a hit they can't answer), sidestep out of their cone when they're aimed at
    us (dodging their strike), and rotate to re-aim otherwise. Sidestepping
    perpendicular keeps us in the melee band while denying the opponent its hit."""
    if aimed and not opp_aimed:
        return {"type": "attack_melee"}
    if opp_aimed:
        px, py = _unit(-oy, ox)                     # perpendicular: circle their flank
        return {"type": "move", "dx": px * 5.0, "dy": py * 5.0}
    if aimed:
        return {"type": "attack_melee"}
    return {"type": "rotate", "dx": ox, "dy": oy}


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
    # `defend` only reduces damage when the attacker is within the +/-22.5 cone
    # BEHIND us, so it takes a deliberate turn-away to make it do anything.
    facing_away = aim <= -CONE

    # Is the opponent currently aimed at us? (Only a threat when it's aimed.)
    ofx, ofy = state.get("opponent_facing", {}).get("dx", 0.0), \
        state.get("opponent_facing", {}).get("dy", 0.0)
    ofl = math.hypot(ofx, ofy) or 1.0
    opp_aim = (ofx * -ox + ofy * -oy) / (ofl * dist) if dist else 1.0
    opp_aimed = opp_aim >= CONE

    hp = state.get("own_hp", 100)
    opp_hp = state.get("opponent_hp", 100)
    cd = state.get("ranged_cooldown_remaining", 0)
    uses = state.get("ranged_uses_remaining", 0)

    if not isinstance(memory, dict):
        memory = {}
    tick = memory.get("tick", state.get("tick", 0))
    # Is the opponent closing on us? Turning our back on a bot that's charging in
    # is suicide; turning it on one that's holding range is how defend pays off.
    prev_dist = memory.get("dist", dist)
    closing = dist < prev_dist - 0.5
    new_mem = {"hp": hp, "tick": tick + 1, "dist": dist}

    # Phase 1 (opening): defensive posture. Prefer range, don't dive into melee,
    # and turtle (turn away + defend) only in the window where we genuinely
    # cannot retaliate — otherwise hitting back beats halving a hit.
    if tick < DEFEND_TICKS:
        # Free 15-damage ranged shot when aimed and in range — always worth it.
        if aimed and uses > 0 and cd == 0 and dist <= RANGED_R:
            return {"type": "attack_ranged"}, new_mem
        # Forced into melee: flank-dodge — hit when they can't answer, sidestep
        # their strike otherwise, rather than trading blows one-for-one.
        if dist <= MELEE_R + 0.5:
            return _melee(ox, oy, aimed, opp_aimed), new_mem
        # Ranged threat we can't answer (shot spent or on a long cooldown) from an
        # opponent holding its distance: turn our back to it and defend, halving
        # the incoming 15s. Requires enough cooldown left to turn back around
        # (180 deg = 2 ticks), and never against someone closing for melee.
        if (dist <= RANGED_R and dist > TURTLE_MIN_R and not closing
                and (uses == 0 or cd > TURN_BACK_TICKS)):
            if facing_away:
                return {"type": "defend"}, new_mem
            return {"type": "rotate", "dx": -ox, "dy": -oy}, new_mem
        # Not aimed: turn toward the opponent so we can fire / track next tick.
        if not aimed:
            return {"type": "rotate", "dx": ox, "dy": oy}, new_mem
        # Out of ranged range: edge in until we can shoot.
        if dist > RANGED_R:
            ux, uy = _unit(ox, oy)
            step = min(dist - RANGED_R + 1.0, 5.0)
            return {"type": "move", "dx": ux * step, "dy": uy * step}, new_mem
        # In range, aimed, shot nearly ready: hold aim so it lands on cooldown end.
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Phase 2 (attack mode) ------------------------------------------------
    # 1. Ranged: best damage per hit; use whenever aimed and in range.
    if uses > 0 and cd == 0 and dist <= RANGED_R:
        if aimed:
            return {"type": "attack_ranged"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 2. Melee when adjacent — flank-dodge to win the exchange, not just trade.
    if dist <= MELEE_R + 0.5:
        return _melee(ox, oy, aimed, opp_aimed), new_mem

    # 3. Close distance. Rotate first if badly off-aim so we can act next tick.
    if not aimed:
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Aim for the melee band; move directly toward the opponent.
    ux, uy = _unit(ox, oy)
    step = min(dist - MELEE_R + 1.0, 5.0)
    return {"type": "move", "dx": ux * step, "dy": uy * step}, new_mem
