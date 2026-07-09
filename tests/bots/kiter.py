def decide(state, memory):
    if state["ranged_cooldown_remaining"] == 0 and state["ranged_uses_remaining"] > 0:
        return {"type": "attack_ranged"}, memory

    dx = state["own_position"]["x"] - state["opponent_position"]["x"]
    dy = state["own_position"]["y"] - state["opponent_position"]["y"]
    return {"type": "move", "dx": dx, "dy": dy}, memory
