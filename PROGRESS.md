# PROGRESS.md

Running log for the TIC-80 Space Invaders cartridge. Read `MISSION.md` for what to
build and `AGENTS.md` for how to work; this file records where things actually stand.

**Update rule:** every milestone ends with an edit here — what shipped, what was
decided, what is still open (`AGENTS.md` §6). Do not mark a milestone done without
having loaded the cart and observed the behavior (`AGENTS.md` §3.4).

---

## 1. Milestone status

Legend: `TODO` · `IN PROGRESS` · `DONE` (verified in-console) · `BLOCKED`

| # | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Skeleton — metadata header, `TIC()`, `cls()`, "HELLO", scaffolding | TODO | Next up. No `game.lua` exists yet. |
| M1 | Player — movement, edge clamp, single bullet | TODO | |
| M2 | Fleet — 5 × 11 grid, stepped march, drop-and-reverse, waddle | TODO | |
| M3 | Combat — bullet kills, scoring, speed-up curve | TODO | |
| M4 | Threat — enemy fire, death, lives, game over | TODO | |
| M5 | Bunkers — cell-grid erosion, per-wave reset | TODO | |
| M6 | Mystery ship — spawn timing, traversal, bonus | TODO | |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | TODO | |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** environment ready, no code written. Start at M0.

---

## 2. Environment

Verified 2026-08-16 on WSL2 / Ubuntu 26.04 LTS (x86_64).

| Component | State |
|---|---|
| TIC-80 | `/usr/bin/tic80`, version **1.1.2837 (be42d6f)** — installed from the v1.1 GitHub release `.deb` |
| Lua (host-side, for syntax checks only) | `lua5.4` / `luac5.4` at `/usr/bin/` |
| Display | WSLg — `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`; GUI window renders |
| Audio | working; `libpulse0` installed, SDL connects to WSLg's PulseServer at `unix:/mnt/wslg/PulseServer` |
| Repo | https://github.com/olavostauros/stauros-invaders (public), branch `master` |

Run loop (verify flags against `tic80 --help` for this build):

```bash
tic80 --fs=. --cmd="load game.lua & run"
```

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3):

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

- **2026-08-16 — Installed TIC-80 from the prebuilt v1.1 `.deb` rather than building
  from source.** There is no `tic80` package in the Ubuntu archive. The release binary
  statically links SDL2 and `ldd` showed no missing libraries, so it runs as-is;
  building from source would have pulled in the full cmake/SDL/ruby/wayland toolchain
  for no benefit at this version. Revisit only if a post-1.1 feature is needed.
- **2026-08-16 — Repo is public, default branch `master`.** Branch name is git's
  default at init; not a deliberate choice, and cheap to rename while history is one
  commit deep.
- **2026-08-16 — `.gitignore` covers `scratch/` and `*.tic` only** (plus editor/OS
  cruft). `game.lua` and `docs/` are tracked deliverables per `AGENTS.md` §1 and §4.4.

---

## 4. API documentation status

`AGENTS.md` §4.1 requires every TIC-80 function's signature to be looked up and
recorded in `docs/tic80-api.md` **before its first use**.

- `docs/` — **not yet created.** No API functions verified yet.
- Lua version reported by the console — **unconfirmed.** Run `trace(_VERSION)` in-cart
  during M0 and record it in `docs/lua-notes.md`. Do not assume it matches the
  host-side `lua5.4` installed above.

---

## 5. Known bugs

None — there is no code yet.

---

## 6. OPEN QUESTIONS

Per `AGENTS.md` §4.5: state the question, implement around it under a clearly stated
assumption, and record the assumption here. Mark answered ones `RESOLVED:` with the
answer and its source; do not delete them.

- **Does `AGENTS.md` §1's stated repo root need correcting?** It says
  `/home/tic-80/game`, but the actual working tree is `/home/tic-80/stauros-invaders`.
  Cosmetic, but it is wrong in a public repo. Awaiting the user's call.
- **Which Lua version does TIC-80 1.1.2837 embed?** Blocks any use of version-specific
  syntax (integer division, `goto`, bitwise operators). Resolve in M0 via
  `trace(_VERSION)`.
