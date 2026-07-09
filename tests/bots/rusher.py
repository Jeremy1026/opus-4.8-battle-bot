import math


def decide(state, memory):
    dx = state["opponent_position"]["x"] - state["own_position"]["x"]
    dy = state["opponent_position"]["y"] - state["own_position"]["y"]
    distance = math.hypot(dx, dy)

    facing_dx = state["own_facing"]["dx"]
    facing_dy = state["own_facing"]["dy"]
    facing_length = math.hypot(facing_dx, facing_dy)
    aim_dot = (facing_dx * dx + facing_dy * dy) / (facing_length * distance) if distance > 0 else 1.0
    if aim_dot < 0.95:
        return {"type": "rotate", "dx": dx, "dy": dy}, memory

    if distance <= 5.0:
        return {"type": "attack_melee"}, memory

    return {"type": "move", "dx": dx, "dy": dy}, memory
