# Ronin

An adaptive-hybrid combat bot for the [LLM Robots battle platform](https://battlellmrobots.com).

## Strategy

Ronin plays in two phases.

**Opening (first 20 ticks) — defense-leaning.** It preserves HP and range: it
fires free ranged shots when aimed and in range, edges in only when out of
ranged range, and otherwise holds distance and tracks the opponent — it does
*not* dive into melee. If the opponent forces contact it melee-counters rather
than standing still.

`defend` only halves damage when the attacker is within the ±22.5° cone
*behind* you, so using it takes a deliberate turn-away. Ronin turtles
(rotate away, then `defend`) only when both hold:

- the opponent is a ranged threat it **can't answer** (shots spent, or a
  cooldown long enough to turn back around — 180° takes 2 ticks), and
- the opponent is **holding its distance**, not closing.

Against anyone charging in it never turns its back. In melee it uses a
**flank-dodge** (see below) rather than turning away.

### Melee flank-dodge

Trading blows one-for-one against a mirror only ever draws. Instead, whenever
Ronin is in the melee band it reads the opponent's facing:

- **Opponent aimed at us** → sidestep perpendicular, out of its ±22.5° cone, so
  its strike misses. (A 5-unit step keeps us inside our own melee range.)
- **Opponent *not* aimed at us** (mid-rotation, facing away) → strike for a hit
  it can't answer.

This makes Ronin take little or no melee damage from aggressive rushers while
still chipping them down with ranged fire. Note it can't help in a pure ranged
duel: at 30 units a single sidestep only shifts ~9.5°, far short of the ±22.5°
cone, so long-range shots are undodgeable and trade evenly.

**Attack mode (tick 20 onward).** It switches to the aggressive priority order
below, actively closing to the melee band.

Within attack mode it evaluates one action per tick in priority order:

1. **Ranged first** — 15 dmg at up to 30 units is the best value, so it fires its 5
   shots whenever it's aimed and in range (rotating to aim if not), rather than hoarding them.
2. **Melee** — once inside 5 units it uses the flank-dodge above: strike when the
   opponent can't answer, sidestep out of its cone when it's aimed at us.
3. **Position** — otherwise it closes to the melee band, rotating first when badly off-aim
   so it can act on the following tick.

Facing only changes via `rotate` (max 90°/tick), and attacks only land within a ±22.5°
cone, so aiming is treated as a hard gate before every attack. A tiny JSON-serializable
memory tracks last-tick HP (to detect incoming damage) and the opponent's last position.

## Files

- `bot.py` — the `decide(state, memory)` entry point (imports only `math`).
- `bot.yaml` — leaderboard metadata (`name`, `llm`).

## Testing

A local harness (`tests/sim.py`) reimplements the documented arena mechanics and runs full
matches against the platform's example bots.

```bash
python -m pytest
```

Ronin currently defeats the documented Rusher, Kiter, and a stationary dummy.

## Submission

Push this repository to a **public** GitHub repo with `bot.py` and `bot.yaml` at the root,
then register the repo URL on battlellmrobots.com. The `tests/` and `docs/` directories are
development-only and are ignored by the platform.
