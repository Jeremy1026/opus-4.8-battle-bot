# Ronin

An adaptive-hybrid combat bot for the [LLM Robots battle platform](https://battlellmrobots.com).

## Strategy

Ronin plays in two phases.

**Opening (first 20 ticks) — defense-leaning.** It preserves HP and range: it
fires free ranged shots when aimed and in range, edges in only when out of
ranged range, and otherwise holds distance and tracks the opponent — it does
*not* dive into melee. If the opponent forces contact it melee-counters rather
than standing still. (Note: `defend` is deliberately never used — on this
platform it only reduces damage when facing *away* from the attacker, so a
bot that faces its target gains nothing from it and just wastes the tick.)

**Attack mode (tick 20 onward).** It switches to the aggressive priority order
below, actively closing to the melee band.

Within attack mode it evaluates one action per tick in priority order:

1. **Ranged first** — 15 dmg at up to 30 units is the best value, so it fires its 5
   shots whenever it's aimed and in range (rotating to aim if not), rather than hoarding them.
2. **Melee** — once inside 5 units it strikes for 10 dmg when aimed, rotating to aim otherwise.
3. **Defend** — when adjacent, off-aim, actively taking damage, and not ahead on HP,
   it halves the incoming hit instead of trading blows it would lose.
4. **Position** — otherwise it closes to the melee band, rotating first when badly off-aim
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
