# Vanguard Battle Bot — Design

Date: 2026-07-08
Platform: https://battlellmrobots.com

## Goal

Build a competitive 1v1 bot for the LLM Robots battle platform using an
adaptive hybrid strategy: use ranged shots opportunistically while closing
distance, then dominate with aimed melee, defending reactively when caught.

## Platform constraints (from documentation.md)

- Arena 100×100, hard walls (movement clamped). Bot radius 2.
- Starting HP 100. Match ends on KO, at 500 ticks (higher HP wins), or forfeit.
- Movement: max 5 units/tick (oversized moves scaled).
- Melee: 5-unit range, 10 damage.
- Ranged: 30-unit range, 15 damage, 10-tick cooldown, 5 shots max/match.
- Defend: 0.5× incoming damage, blocks movement/attacks that tick, only works
  when facing *away* from the attacker.
- Facing only changes via `rotate`; turn rate 90°/tick. Attacks hit only within
  a ±22.5° cone of facing (dot product ≥ ~0.924).
- 100ms timeout per `decide()`.
- Allowed imports: math, itertools, functools, heapq, bisect only.
- Disallowed builtins: eval/exec/open/getattr/setattr/globals/etc., dunder
  access, `.format`/`.format_map`, wildcard imports.

## Files

- `bot.py` — top-level `decide(state, memory) -> (action, memory)`.
- `bot.yaml` — `name: Vanguard`, `llm: Claude Opus 4.8`.

## Decision logic (priority order each tick)

1. Compute vector to opponent, distance, and aim dot vs `own_facing`.
2. Ranged: if uses remain, cooldown is 0, opponent within 30, and aimed → fire.
   If in ranged range but not aimed → rotate toward opponent.
3. Melee: if within 5 units and aimed → melee. If within 5 but not aimed →
   rotate.
4. Defend: if we are likely to be hit this tick (opponent within ~5 and we are
   off-aim so we cannot land our own strike) and our HP is not already winning,
   defend.
5. Positioning: otherwise move toward an engagement band — close the gap when
   out of range, avoid overshooting, and steer away from walls to avoid being
   cornered. Rotate to face opponent while moving when not otherwise acting.

## Memory

JSON-serializable, small:
- `prev_opp` — opponent position last tick, for velocity estimation / aim lead.
- `prev_hp` — our HP last tick, to detect we are taking damage.

## Testing

Local harness script simulating the documented mechanics: run Vanguard against
the doc's Rusher and Kiter example bots, plus a stationary dummy, over full
matches; assert Vanguard wins or draws and never emits an invalid action or
raises. Verify no disallowed imports/builtins via a static check.

## Non-goals (YAGNI)

- No pathfinding / obstacle avoidance beyond wall steering (arena is empty).
- No opponent-classification ML; simple heuristics only.
