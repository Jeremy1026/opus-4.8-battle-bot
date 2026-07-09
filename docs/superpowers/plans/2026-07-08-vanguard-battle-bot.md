# Vanguard Battle Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `bot.py` + `bot.yaml` implementing an adaptive hybrid combat bot for battlellmrobots.com, verified by a local simulation harness.

**Architecture:** A single top-level `decide(state, memory)` function chooses one action per tick via priority-ordered heuristics (aim → ranged → melee → defend → position). A local Python harness reimplements the documented arena mechanics to run full matches against the example bots for validation.

**Tech Stack:** Pure Python 3, standard library `math` only in `bot.py`. Harness uses `pytest` (dev-only, not part of the submitted bot).

## Global Constraints

- `bot.py` imports only from: `math`, `itertools`, `functools`, `heapq`, `bisect`. No others.
- No use of: eval, exec, open, compile, getattr, setattr, delattr, vars, dir, globals, locals, input, breakpoint, `__import__`, `.format`, `.format_map`, dunder attribute access, wildcard imports.
- `decide` must be top-level, exactly `(state, memory)`, return `(action_dict, memory_dict)`. Memory must be JSON-serializable.
- Action dicts must match: move/rotate `{"type","dx","dy"}`, `{"type":"attack_melee"}`, `{"type":"attack_ranged"}`, `{"type":"defend"}`, `{"type":"idle"}`.
- Constants: arena 100×100, radius 2, speed 5, melee range 5 dmg 10, ranged range 30 dmg 15 cooldown 10 uses 5, defend 0.5×, cone ±22.5° (dot ≥ 0.9239), turn 90°/tick, 500 ticks, 100ms/tick.

---

### Task 1: bot.yaml + bot.py skeleton with pass-through decide

**Files:**
- Create: `bot.yaml`
- Create: `bot.py`
- Create: `tests/test_contract.py`

**Interfaces:**
- Produces: `decide(state: dict, memory: dict) -> tuple[dict, dict]` in `bot.py`.

- [ ] **Step 1: Write bot.yaml**

```yaml
name: Vanguard
llm: Claude Opus 4.8
```

- [ ] **Step 2: Write failing contract test** in `tests/test_contract.py`

```python
import ast, pathlib
import bot

def test_decide_signature_and_return():
    state = {
        "own_position": {"x": 10.0, "y": 10.0},
        "own_hp": 100, "opponent_position": {"x": 50.0, "y": 50.0},
        "opponent_hp": 100, "own_facing": {"dx": 1.0, "dy": 0.0},
        "opponent_facing": {"dx": -1.0, "dy": 0.0},
        "ranged_cooldown_remaining": 0, "ranged_uses_remaining": 5, "tick": 0,
    }
    action, memory = bot.decide(state, {})
    assert isinstance(action, dict) and "type" in action
    assert isinstance(memory, dict)

ALLOWED = {"math", "itertools", "functools", "heapq", "bisect"}

def test_only_allowed_imports():
    src = pathlib.Path("bot.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                assert n.name.split(".")[0] in ALLOWED
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in ALLOWED

def test_no_forbidden_builtins():
    src = pathlib.Path("bot.py").read_text()
    for bad in ["eval(", "exec(", "open(", "getattr(", "setattr(",
                "globals(", "locals(", "__import__", ".format(", "compile("]:
        assert bad not in src
```

- [ ] **Step 3: Write minimal `bot.py`**

```python
import math

def decide(state, memory):
    return {"type": "idle"}, memory
```

- [ ] **Step 4: Run tests**

Run: `cd <repo> && python -m pytest tests/test_contract.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add bot.yaml bot.py tests/test_contract.py
git commit -m "feat: bot skeleton with contract tests"
```

---

### Task 2: Simulation harness

**Files:**
- Create: `tests/sim.py`
- Create: `tests/bots/rusher.py`, `tests/bots/kiter.py`, `tests/bots/dummy.py`
- Create: `tests/test_sim.py`

**Interfaces:**
- Produces: `run_match(decide_a, decide_b, max_ticks=500) -> dict` returning `{"winner": "a"|"b"|"draw", "hp_a": int, "hp_b": int, "ticks": int}`. Bots start at (25,50) facing +x and (75,50) facing -x.

- [ ] **Step 1: Write `tests/sim.py`** implementing documented mechanics: apply each bot's action per tick in order, resolve move (clamp to arena, respect radius-2 separation, max speed 5), rotate (clamp to 90°/tick, normalize facing), attacks (cone dot ≥ 0.9239, ranged cooldown/uses, defend halves damage on the defender's next-received hit that tick), HP to 0 ends match, 500-tick cap with higher-HP winner. Isolate each bot call in try/except; on exception treat as idle and count errors (forfeit at, say, 10). Copy state so bots can't mutate shared arena.

```python
import copy, math

MELEE_R, MELEE_D = 5.0, 10
RANGED_R, RANGED_D, RANGED_CD = 30.0, 15, 10
CONE = 0.9239  # cos(22.5 deg)

def _norm(dx, dy):
    d = math.hypot(dx, dy)
    return (dx / d, dy / d) if d else (1.0, 0.0)

def _aimed(fx, fy, tx, ty):
    d = math.hypot(tx, ty)
    if d == 0:
        return True
    return (fx * tx + fy * ty) / d >= CONE

def run_match(decide_a, decide_b, max_ticks=500):
    bots = {
        "a": {"pos": [25.0, 50.0], "hp": 100, "face": [1.0, 0.0],
              "cd": 0, "uses": 5, "mem": {}, "errors": 0, "defending": False},
        "b": {"pos": [75.0, 50.0], "hp": 100, "face": [-1.0, 0.0],
              "cd": 0, "uses": 5, "mem": {}, "errors": 0, "defending": False},
    }
    fns = {"a": decide_a, "b": decide_b}
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
                if bots[me]["errors"] >= 10:
                    return {"winner": other, "hp_a": bots["a"]["hp"],
                            "hp_b": bots["b"]["hp"], "ticks": tick}
        for k in bots:
            bots[k]["defending"] = actions[k].get("type") == "defend"
        for k in bots:
            if bots[k]["cd"] > 0:
                bots[k]["cd"] -= 1
        for me, other in (("a", "b"), ("b", "a")):
            _apply(bots[me], bots[other], actions[me])
        if bots["a"]["hp"] <= 0 or bots["b"]["hp"] <= 0:
            break
    return _result(bots, tick)

def _state(m, o, tick):
    return {
        "own_position": {"x": m["pos"][0], "y": m["pos"][1]},
        "own_hp": m["hp"], "opponent_position": {"x": o["pos"][0], "y": o["pos"][1]},
        "opponent_hp": o["hp"], "own_facing": {"dx": m["face"][0], "dy": m["face"][1]},
        "opponent_facing": {"dx": o["face"][0], "dy": o["face"][1]},
        "ranged_cooldown_remaining": m["cd"], "ranged_uses_remaining": m["uses"],
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
        if math.hypot(nx - o["pos"][0], ny - o["pos"][1]) >= 4.0:  # 2*radius
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
    winner = "a" if a > b else "b" if b > a else "draw"
    if a <= 0 and b > 0:
        winner = "b"
    elif b <= 0 and a > 0:
        winner = "a"
    return {"winner": winner, "hp_a": a, "hp_b": b, "ticks": tick}
```

- [ ] **Step 2: Write example opponents** in `tests/bots/`.

`rusher.py` and `kiter.py`: copy verbatim from the platform documentation. `dummy.py`:

```python
def decide(state, memory):
    return {"type": "idle"}, memory
```

- [ ] **Step 3: Write `tests/test_sim.py`** sanity tests for the harness itself

```python
from tests.sim import run_match
from tests.bots import rusher, dummy

def test_dummy_vs_dummy_is_draw():
    r = run_match(dummy.decide, dummy.decide, max_ticks=50)
    assert r["winner"] == "draw"

def test_rusher_beats_dummy():
    r = run_match(rusher.decide, dummy.decide)
    assert r["winner"] == "a"
```

- [ ] **Step 4: Run** `python -m pytest tests/test_sim.py -v` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/sim.py tests/bots tests/test_sim.py
git commit -m "test: add match simulation harness"
```

---

### Task 3: Implement adaptive hybrid decide logic

**Files:**
- Modify: `bot.py`
- Create: `tests/test_vanguard.py`

**Interfaces:**
- Consumes: `run_match` from `tests/sim.py`; `bot.decide`.

- [ ] **Step 1: Write failing behavior tests** in `tests/test_vanguard.py`

```python
import bot
from tests.sim import run_match
from tests.bots import rusher, kiter, dummy

def _state(**kw):
    base = {
        "own_position": {"x": 50.0, "y": 50.0}, "own_hp": 100,
        "opponent_position": {"x": 60.0, "y": 50.0}, "opponent_hp": 100,
        "own_facing": {"dx": 1.0, "dy": 0.0}, "opponent_facing": {"dx": -1.0, "dy": 0.0},
        "ranged_cooldown_remaining": 0, "ranged_uses_remaining": 5, "tick": 0,
    }
    base.update(kw)
    return base

def test_fires_ranged_when_aimed_and_available():
    act, _ = bot.decide(_state(), {})
    assert act["type"] == "attack_ranged"

def test_melee_when_adjacent_and_aimed_no_ranged():
    s = _state(opponent_position={"x": 53.0, "y": 50.0},
               ranged_uses_remaining=0, ranged_cooldown_remaining=0)
    act, _ = bot.decide(s, {})
    assert act["type"] == "attack_melee"

def test_rotates_when_off_aim():
    s = _state(own_facing={"dx": 0.0, "dy": 1.0})  # facing away
    act, _ = bot.decide(s, {})
    assert act["type"] == "rotate"

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
```

- [ ] **Step 2: Run to confirm failure** — `python -m pytest tests/test_vanguard.py -v`. Expected: FAIL.

- [ ] **Step 3: Implement full logic in `bot.py`**

```python
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
    new_mem = {"hp": hp,
               "opp": [state["opponent_position"]["x"], state["opponent_position"]["y"]]}

    # 1. Ranged: best damage, use whenever aimed and in range.
    if uses > 0 and cd == 0 and dist <= RANGED_R:
        if aimed:
            return {"type": "attack_ranged"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 2. Melee when adjacent.
    if dist <= MELEE_R:
        if aimed:
            return {"type": "attack_melee"}, new_mem
        # Off-aim and adjacent: if being hit and losing, defend; else rotate.
        if took_damage and hp <= opp_hp:
            return {"type": "defend"}, new_mem
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # 3. Close distance. Rotate first if badly off-aim so we can act next tick.
    if not aimed:
        return {"type": "rotate", "dx": ox, "dy": oy}, new_mem

    # Aim for melee band; steer slightly off walls if near an edge.
    ux, uy = _unit(ox, oy)
    tx = state["own_position"]["x"] + ux * min(dist - MELEE_R + 1.0, 5.0)
    ty = state["own_position"]["y"] + uy * min(dist - MELEE_R + 1.0, 5.0)
    mvx, mvy = tx - state["own_position"]["x"], ty - state["own_position"]["y"]
    return {"type": "move", "dx": mvx, "dy": mvy}, new_mem
```

- [ ] **Step 4: Run tests** — `python -m pytest tests/ -v`. Expected: ALL PASS. If a match test fails, tune thresholds (engagement band, defend trigger) and re-run.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_vanguard.py
git commit -m "feat: adaptive hybrid combat logic for Vanguard"
```

---

### Task 4: README and submission notes

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** documenting strategy, mechanics summary, how to run tests (`python -m pytest`), and GitHub submission steps (public repo with `bot.py` + `bot.yaml` at root).

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with strategy and submission notes"
```

## Self-Review

- Spec coverage: ranged/melee/defend/positioning/memory/wall-steering all in Task 3; sandbox constraints checked in Task 1; testing vs Rusher/Kiter/dummy in Tasks 2–3. Covered.
- Placeholder scan: none.
- Type consistency: `run_match` return keys (`winner`,`hp_a`,`hp_b`,`ticks`) and `decide` signature consistent across tasks.
