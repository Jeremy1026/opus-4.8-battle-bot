import ast
import pathlib

import bot

ALLOWED = {"math", "itertools", "functools", "heapq", "bisect"}
BOT_SRC = pathlib.Path(__file__).resolve().parent.parent / "bot.py"


def test_decide_signature_and_return():
    state = {
        "own_position": {"x": 10.0, "y": 10.0},
        "own_hp": 100,
        "opponent_position": {"x": 50.0, "y": 50.0},
        "opponent_hp": 100,
        "own_facing": {"dx": 1.0, "dy": 0.0},
        "opponent_facing": {"dx": -1.0, "dy": 0.0},
        "ranged_cooldown_remaining": 0,
        "ranged_uses_remaining": 5,
        "tick": 0,
    }
    action, memory = bot.decide(state, {})
    assert isinstance(action, dict) and "type" in action
    assert isinstance(memory, dict)


def test_only_allowed_imports():
    tree = ast.parse(BOT_SRC.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                assert n.name.split(".")[0] in ALLOWED
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in ALLOWED


def test_no_forbidden_builtins():
    src = BOT_SRC.read_text()
    for bad in ["eval(", "exec(", "open(", "getattr(", "setattr(",
                "globals(", "locals(", "__import__", ".format(", "compile("]:
        assert bad not in src
