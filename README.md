# Stauros Invaders

A Space Invaders clone for the [TIC-80](https://tic80.com) fantasy console, written in
Lua as a single cartridge.

This file covers **what you need installed and how to run the thing**. The other
documents cover everything else:

| File | Contents |
|---|---|
| `MISSION.md` | What the game is — spec, entities, state machine, and the M0–M8 milestone plan |
| `AGENTS.md` | How to work in this repo — hard constraints of the target, documentation rules, conventions |
| `LINT-RULES.md` | Numbered lint rules for `game.lua` and the commands that check them |
| `PROGRESS.md` | Where the project actually stands — milestone status, decisions and their rationale, open questions |
| `docs/` | Verified TIC-80 API signatures and Lua notes, cached from the official wiki |

Read `AGENTS.md` and `MISSION.md` before changing code.

---

## Requirements

Verified 2026-08-16 on Ubuntu 26.04 LTS (x86_64) under WSL2, kernel
`6.18.33.2-microsoft-standard-WSL2`.

### Required

| Tool | Version here | Purpose |
|---|---|---|
| TIC-80 | 1.1.2837 (be42d6f) | The console. Runs the cartridge |
| Python 3 | 3.14.4 | Runs `pack.py`, which builds the loadable cart |
| Git | 2.53.0 | Version control |

### Recommended

| Tool | Version here | Purpose |
|---|---|---|
| `luac5.4` | Lua 5.4.8 | Fast syntax check without launching the console |

Nothing is needed for screenshots — see *Seeing the screen* below. A working WSLg
display is needed only for the frame-rate check, which must run windowed.

### Installing TIC-80

There is no `tic80` package in the Ubuntu archive. Install the prebuilt `.deb` from the
[v1.1 GitHub release](https://github.com/nesbox/TIC-80/releases). It statically links
SDL2 and needs no further dependencies.

Building from source is not necessary at this version — see the rationale in
`PROGRESS.md` §3.

### Installing the rest

```bash
sudo apt-get install -y python3 lua5.4
```

---

## Two things that will surprise you

Both are verified, both shaped how this repo works, and both are easy to lose a
morning to.

### The console is not PRO, and non-PRO builds refuse text cartridges

`load game.lua` fails outright:

> This version only supports binary .png or .tic cartridges. TIC-80 PRO is needed for
> text files.

So `game.lua` gets packed into a minimal binary `.tic` before every run. That is all
`pack.py` does — it writes a single `CHUNK_CODE` chunk containing the source verbatim.
`game.lua` stays the only tracked deliverable; `game.tic` is generated and gitignored.

If you would rather not pack, the TIC-80 README sanctions building PRO yourself with
`cmake .. -DBUILD_PRO=On`, which restores plain `load game.lua`.

### The console runs Lua 5.3, not 5.4

`trace(_VERSION)` in-console reports **Lua 5.3**. The host `luac5.4` used for syntax
checking is a *superset*, so it will happily accept 5.4-only syntax — `<close>`,
`<const>`, `warn()`, `coroutine.close` — that the cartridge then fails to load with.

Integer division, `goto`, and the bitwise operators are all fine. Details and the full
list of what 5.3 does and does not have are in `docs/lua-notes.md`.

Installing `lua5.3` (in the archive as `5.3.6-3`) would make the syntax check match the
target and is worth doing if you touch anything version-sensitive.

---

## Running the game

```bash
python3 pack.py                                        # game.lua -> game.tic
tic80 --fs=. --skip --cmd="load game.tic & run"        # windowed
```

Headless, which prints console output and `trace()` to stdout — enough to confirm a cart
loads and runs without errors:

```bash
tic80 --fs=. --cli --skip --cmd="load game.tic & run"
```

**Re-run `pack.py` after every edit.** The console loads the binary, not the source, so
a stale `game.tic` silently shows you the previous build. This is checked as
`LINT-RULES.md` L050.

A headless run proves the cart loads and does not error. It proves nothing about what is
on screen — see below.

### Seeing the screen, without a screenshot tool

No screenshot tool works in this environment. `grim` fails because WSLg's compositor is
not wlroots-based (`compositor doesn't support wlr-screencopy-unstable-v1`), and no
Wayland tool will do better; no X11 capture tool is installed, and installing one needs
a sudo password, so an agent cannot do it unattended.

None is needed. TIC-80's framebuffer is just RAM — VRAM starts at byte 0 and the screen
is 240 × 136 4-bit pixels — so the console can be asked what it drew:

```bash
python3 tools/screendump.py
```

That appends `tools/vram-probe.lua` to a copy of `game.lua`, wrapping the cart's own
`TIC()` so the code under test runs unmodified, dumps every pixel through `peek4()`, and
prints a palette histogram, the bounding box of everything non-black, and the occupied
region as ASCII. For the M0 cart:

```
palette histogram (. is index 0):
  .:  32564 px (99.77%)
  c:     76 px ( 0.23%)

non-black bounding box: x 105..133 (29 px), y 64..68 (5 px)
margins: left 105, right 106, top 64, bottom 67

 64 |  ##  # ##### ##    ##     ###
 65 |  ##  # ##    ##    ##    ##  #
 66 |  ##### ####  ##    ##    ##  #
 67 |  ##  # ##    ##    ##    ##  #
 68 |  ##  # ##### ##### #####  ###
```

This is better than a screenshot for the checks that matter: it gives exact pixel
coordinates and palette indices, which is what catches text drawn in an invisible color
or off by a pixel. It is `LINT-RULES.md` L051.

Add `--hold <mask> --frames <n>` to dump a frame mid-action instead of at rest — see
below for what the mask is.

Some frames cannot be counted to. The console seeds `math.random` from the clock, so the
ship dies on a different frame every run and the mystery ship arrives 15 to 25 seconds in;
`--state <NAME>` waits for a game state and `--ufo` waits for the saucer to be wholly on
screen. Both usually want `--lives 3`, which pins the life count so the game does not end
before the frame you are waiting for arrives.

`--boom` waits for an explosion to be alight and `--bonus` for the number a shot-down
saucer leaves behind — neither is on screen for long, and which invader a shot reaches
depends on where the fleet has marched to.

Two screens need more than waiting. `--clear <frame>` empties the fleet, which is the only
way to reach the wave banner — killing 55 invaders by holding fire takes tens of thousands
of frames and the ship is shot down first. And `--state GAME_OVER` wants the default
`--hold 0`: fire leaves a game over on the frame after it arrives, so a dump holding the
button waits for a screen it keeps walking out of.

The probes press past the title screen on their own, on frames they do not count, so a
frame number here still means a frame of play. `--state TITLE` is the exception — it dumps
the title itself.

### Pressing buttons, without a keyboard

Nothing here can press a key: WSLg takes input from the Windows side, and no injection
tool is installed. But the gamepad is also just RAM — 4 bytes at `0x0FF80`, one bit per
button — so it can be written directly:

```bash
python3 tools/inputsim.py
```

That appends `tools/input-probe.lua` to a copy of `game.lua`, writes the player-1
gamepad byte before each frame, and traces the `game` table afterwards, so behavior is
read out of the game's own state rather than guessed at. Masks are `1 << button`:
left is 4, right 8, fire 16, so `--hold 24` is right-plus-fire.

A script is written as `[(1, LEFT), (1, RIGHT)] * 1400` and shipped as its shortest
repeating cycle plus a count: the cart holds `game.lua`, the probe and the script table in
one 64 KB chunk, and the table is the only part that grows with the length of a run
(`LINT-RULES.md` L064).

`run()` takes five forcings for states a script cannot reach in reasonable time, each
standing in for a player action: `clear_at` kills the remaining invaders on a frame, `keep`
leaves that many standing instead, `fleet_at` teleports the fleet, `lives` holds the life
count so a long run outlives the threat, and `rush` caps the mystery ship's wait. There is
deliberately no forcing that spawns one — waiting is reachable, and staging the spawn would
delete the thing being measured. This is `LINT-RULES.md` L056.

```
hold fire for 300 frames
  PASS  one bullet, not a stream: 1 bullet(s) spawned in 300 frames of held fire
  PASS  bullet rises 2 px per frame: y 115 -> -1 over 59 frames, step set [2]
```

### Hearing the sound, without speakers

The same trick again, one region over. Nothing here can listen to the console, and the SFX
bank only says what a sound *would* be. What is actually playing is in the sound registers
at `0x0FF9C`: a frequency and a volume per channel, rewritten every frame and zeroed when a
channel goes quiet. `tools/input-probe.lua` traces all four, so a scenario can say which
sound fired, on which channel, on which note, for how long, and that it stopped:

```
  PASS  one note per step, and none without one: every one of 11 steps sounded on the
        frame after it
  PASS  the notes cycle through all four in order: notes [36, 34, 32, 30, 36, 34, 32, ...]
```

Two lags sit between an event and its register, and both are measured rather than assumed:
the register catches up the frame after the `sfx()` call, and `game.lua` changes state at
the end of a frame, so an event's state is the one traced two frames back. This is
`LINT-RULES.md` L065.

**One catch.** `btn` reads that RAM and works perfectly. `btnp` does not — it compares
against a snapshot taken from the real input device, so a poked hold looks like a fresh
press on every frame. The probe supplies its own edge-detecting `btnp` instead, which
means press-versus-hold is checked against the semantics the wiki documents rather than
against the console's own implementation. This is `LINT-RULES.md` L054.

### Checking the frame rate

```bash
python3 tools/fpscheck.py --hold 24
```

Runs windowed, because `--cli` is unthrottled and its frame rate means nothing. It
cross-checks the console's `time()` against the host wall clock, since `time()` alone
would be circular if TIC-80 derived it from the frame counter — it does not. Pass
`--hold` so it measures the milestone's worst case rather than an idle screen. This is
`LINT-RULES.md` L052.

`--hold` only reaches things a button controls. For an entity that arrives on a timer, pass
`--samples <short> <long>` to move the measured window to where it actually is — the default
300 and 1200 can miss the mystery ship entirely.

Each sample also reports the load it was measured under — the state and invader count it
ended on, and across the whole sample how many frames had the saucer up, the most bursts
and the most channels sounding at once, and how many frames made any sound at all. A frame
rate is only as good as what was on screen for it:

```
sample  2400: console FPS 59.999 over 2400 frames in 40001.0 ms   host 41.13 s
            LOAD state PLAYING invaders 49 saucerframes 440 peakbursts 1 peakvoices 4
                 soundingframes 1015
```

## Linting

Before closing a milestone, run the pass from `LINT-RULES.md`. It is `grep`, `awk`, and
`luac5.4`, so it costs seconds. The most useful check lists every global the cartridge
touches, straight out of the bytecode — it catches both accidental globals and TIC-80
calls that were never documented:

```bash
luac5.4 -l -p game.lua | grep -oE '_ENV "[A-Za-z_][A-Za-z0-9_]*"' | sort -u
```

The rules are meant to grow. When a defect gets past them, add the check that would
have caught it (`AGENTS.md` §5 *Linting*).

## Repository layout

```
game.lua        the cartridge — the only file TIC-80 loads
pack.py         packs game.lua into a binary game.tic
README.md       this file
MISSION.md      game design spec + milestone plan
AGENTS.md       operating rules for working in this repo
LINT-RULES.md   lint rules and their check commands
PROGRESS.md     running log: milestone status, decisions, open questions
docs/           cached TIC-80 API signatures, RAM map, and Lua notes
tools/          verification harness: screendump.py, fpscheck.py, inputsim.py, probes
scratch/        throwaway experiments and generated intermediates (gitignored)
```

Do not add build systems, package manifests, or `src/` module trees. TIC-80 loads
exactly one file and has no `require`.
