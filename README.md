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
| `imagemagick` | `8:7.1.2.18` | Screenshots, for verifying anything visual |
| `x11-utils` | `7.7+7build1` | `xwininfo`, to locate the TIC-80 window for capture |

### Installing TIC-80

There is no `tic80` package in the Ubuntu archive. Install the prebuilt `.deb` from the
[v1.1 GitHub release](https://github.com/nesbox/TIC-80/releases). It statically links
SDL2 and needs no further dependencies.

Building from source is not necessary at this version — see the rationale in
`PROGRESS.md` §3.

### Installing the rest

```bash
sudo apt-get install -y python3 lua5.4 imagemagick x11-utils
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

### Screenshots under WSLg

`grim` does **not** work here. WSLg's compositor is not wlroots-based, so it fails with
`compositor doesn't support wlr-screencopy-unstable-v1`, and no Wayland screenshot tool
will do better. Capture through XWayland (`DISPLAY=:0`) instead. Rootless XWayland has
no useful root window, so grab the window by name:

```bash
xwininfo -root -tree | grep -i tic       # find the window id
import -window <id> shot.png
```

The `grim` failure is confirmed; this X11 replacement is the documented approach but has
not yet been exercised here, because `imagemagick` is not installed as of 2026-08-16.

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
docs/           cached TIC-80 API signatures and Lua notes
scratch/        throwaway experiments; never referenced by game.lua (gitignored)
```

Do not add build systems, package manifests, or `src/` module trees. TIC-80 loads
exactly one file and has no `require`.
