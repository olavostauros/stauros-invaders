# MISSION.md

Build a **Space Invaders clone** as a TIC-80 cartridge in Lua.

Working rules live in `AGENTS.md` — read it first. This file defines the game itself
and the order in which it gets built.

---

## 1. Objective

A single-file cartridge, `game.lua`, that plays as a faithful-in-feel clone of the
1978 arcade original, adapted to TIC-80's 240 × 136 display and 60 FPS frame callback.

Faithful in *feel* means: the fleet's stepped march, the acceleration as it thins out,
one player shot in flight at a time, eroding bunkers, the mystery ship. It does not
mean pixel-exact reproduction of the arcade ROM, and it does not mean replicating
arcade bugs or the original's 224 × 256 portrait resolution.

**Definition of finished:** a player can start the game from a title screen, clear
waves of increasing difficulty, lose all three lives, see a game-over screen with
their score, and restart — without the cartridge ever erroring or dropping frames.

---

## 2. Screen layout

240 × 136, origin top-left, y increases downward.

```
y=0    ┌──────────────────────────────────────────────┐
       │ SCORE 00000        HI 00000        LIVES ▲▲▲ │  HUD band, y 0..7
y=8    ├──────────────────────────────────────────────┤
       │              ★  (mystery ship)               │  UFO lane, y ~10
       │                                              │
       │   ▓▓▓▓▓▓▓▓▓▓▓  fleet: 5 rows × 11 columns    │  fleet zone
       │   ▓▓▓▓▓▓▓▓▓▓▓                                │
       │   ▓▓▓▓▓▓▓▓▓▓▓                                │
       │                                              │
       │   ██   ██   ██   ██     bunkers              │  y ~106
       │                                              │
       │              ▲          player               │  y ~120
y=128  ├──────────────────────────────────────────────┤
       │██████████████████████████████████████████████│  ground line
y=136  └──────────────────────────────────────────────┘
```

All coordinates above are targets, not gospel — tune them so the fleet's full
horizontal travel fits and the bottom row has room to descend meaningfully before
reaching the player. Record the final values as named constants.

---

## 3. Entities

### Player
- 8 × 8 sprite, moves left/right only, clamped to the screen edges.
- Speed ~1 px/frame. Buttons: `left` / `right`; fire on `A`.
- Fires with `btnp` semantics, not `btn` — holding fire must not auto-repeat.
- **Exactly one player bullet may be in flight.** The next shot is only allowed after
  the current one leaves the screen or hits something. This constraint is the core of
  the game's pacing; do not relax it.
- Three lives. On death: brief explosion animation, freeze play, respawn at center.

### Invader fleet
- **5 rows × 11 columns = 55 invaders.** Three visual types: top row (30 pts),
  middle two rows (20 pts), bottom two rows (10 pts).
- Two animation frames per type, swapped on each fleet step — the march "waddle".
- The fleet moves as one rigid body: step horizontally by a fixed amount, and when
  *any* live invader touches a screen edge, the whole fleet drops one row and reverses
  direction.
- **Movement is stepped, not continuous.** The fleet advances one discrete step every
  N frames. N shrinks as invaders die — this is the difficulty curve and it must be
  driven by the count of *living* invaders, not by a wave timer.
  Suggested feel: ~55 frames between steps at 55 alive, down to ~2 frames at 1 alive.
  Interpolate; tune by playing.
- Invaders fire downward. Only the **bottom-most living invader in a column** may
  fire. Cap concurrent enemy bullets (start at 3) and gate new shots behind a cooldown.
- The fleet descending to the player's row is an **instant game over**, regardless of
  remaining lives.

### Mystery ship (UFO)
- Crosses the UFO lane horizontally at a constant speed, entering from alternating
  sides, at a randomized interval (~15–25 seconds of play).
- Awards a bonus from a small table of values (50/100/150/300 is a reasonable set).
- Despawns on hit or on leaving the screen. Never present during a wave transition.

### Bunkers
- Four destructible shields between the fleet and the player.
- Each bunker is a small grid of destructible cells, ~2 × 2 px per cell. Store them as
  a table of booleans, draw from that table, and clear cells on impact — do **not**
  fake destruction with sprite swaps.
- Both player and enemy bullets erode them. Invaders passing through a bunker erase it.
- Bunkers reset to full at the start of each wave.

### Bullets
- Player bullet travels up, enemy bullets travel down, ~2 px/frame each.
- Axis-aligned bounding-box collision throughout. No pixel-perfect collision.
- Player bullets and enemy bullets may cancel each other on contact (optional; if
  implemented, make it visible with a small flash).

---

## 4. Game states

A single explicit state machine drives everything. States:

| State | Enters from | Behavior | Exits on |
|---|---|---|---|
| `TITLE` | boot, `GAME_OVER` | Title, high score, "PRESS A" | `A` pressed → `PLAYING` |
| `PLAYING` | `TITLE`, `WAVE_CLEAR`, respawn | Full simulation | death, wave cleared, fleet lands |
| `PLAYER_DEAD` | `PLAYING` | Explosion, input frozen | timer → `PLAYING` or `GAME_OVER` |
| `WAVE_CLEAR` | `PLAYING` (0 invaders) | Brief pause, wave banner | timer → `PLAYING` (next wave) |
| `GAME_OVER` | `PLAYER_DEAD`, fleet landing | Final score, high score | `A` pressed → `TITLE` |

No state may run another state's update logic. `TIC()` dispatches on the current
state and nothing else.

### Wave progression
Each cleared wave: the fleet starts one row lower (capped so it never starts on top
of the bunkers), enemy fire rate increases modestly, and the step-interval curve
tightens. Difficulty must ramp; it must not become unwinnable by wave 3.

---

## 5. Scoring

| Target | Points |
|---|---|
| Bottom two rows | 10 |
| Middle two rows | 20 |
| Top row | 30 |
| Mystery ship | 50 / 100 / 150 / 300 |

- Extra life at 1500 points, once per game.
- High score persists across sessions via `pmem` — a single slot is enough. Verify
  `pmem`'s signature and slot count against the docs before using it (`AGENTS.md` §4.1).

---

## 6. Audio

Keep it minimal and arcade-flavored. Required:
- Player shot
- Invader destroyed
- Player destroyed
- The four-note descending fleet loop, whose tempo tracks the fleet's step interval

Optional: UFO warble, bunker hit, extra life. Build sound effects in TIC-80's SFX
editor and trigger by id; do not attempt to synthesize audio by poking sound registers
unless the SFX editor genuinely cannot produce the sound.

---

## 7. Controls

| Input | Action |
|---|---|
| `left` / `right` (btn 2 / 3) | Move ship |
| `A` (btn 4) | Fire / confirm |

Verify button index constants against the TIC-80 API docs before hardcoding them.

---

## 8. Milestones

Build in this order. Each one ends with a cartridge that runs and is worth looking at.
Do not start a milestone before the previous one meets its acceptance criteria.

**M0 — Skeleton**
Metadata header, `TIC()` with `cls()`, a "HELLO" print, and the constants/state
section scaffolding from `AGENTS.md` §5.
*Accept:* cart loads, screen clears, text visible, 60 FPS.

**M1 — Player**
Player sprite, left/right movement with edge clamping, single bullet with the
one-shot-at-a-time rule.
*Accept:* ship moves smoothly; holding fire produces one bullet, not a stream.

**M2 — Fleet**
55 invaders in a 5 × 11 grid, stepped march, edge detection, drop-and-reverse, the
two-frame waddle animation.
*Accept:* fleet marches edge to edge, drops and reverses correctly, animates in step.

**M3 — Combat**
Player bullet kills invaders, scoring, the speed-up curve tied to living count.
*Accept:* fleet visibly accelerates as it thins; score increments by row value.

**M4 — Threat**
Enemy fire from bottom-most invaders, player death, lives, game over on last life and
on fleet landing.
*Accept:* the game is losable in both ways, and death/respawn reads clearly.

**M5 — Bunkers**
Four cell-grid bunkers, erosion from both directions, reset per wave.
*Accept:* bunkers erode progressively and block bullets while cells remain.

**M6 — Mystery ship**
UFO spawn timing, traversal, bonus scoring.
*Accept:* UFO appears on a randomized interval and awards a bonus when hit.

**M7 — Shell**
Title screen, game-over screen, wave transitions, HUD, `pmem` high score, extra life.
*Accept:* the full loop title → play → game over → title runs without a restart.

**M8 — Audio and polish**
Sound effects, the fleet loop tracking march tempo, explosion animations, screen
juice. Final performance pass.
*Accept:* every §6 required sound fires; 60 FPS holds with a full wave on screen.

---

## 9. Non-goals

Do not build: two-player mode, online leaderboards, a level editor, alternate weapons,
power-ups, parallax backgrounds, an entity-component system, or any engine abstraction
layer. A clone of the original, done well, is the whole job.

---

## 10. Open questions

Append here as they come up; do not delete answered ones — mark them `RESOLVED:` with
the answer and its source.
