# PROGRESS.md

Running log for the TIC-80 Space Invaders cartridge. Read `MISSION.md` for what to
build and `AGENTS.md` for how to work; this file records where things actually stand.

**Update rule:** `AGENTS.md` §3 *Keeping `PROGRESS.md` current* governs this file —
which section takes what, and when to write to it. Update as you go, not only at
milestone end. Do not mark a milestone `DONE` without having loaded the cart and
observed the behavior (`AGENTS.md` §3 rule 4, and §6).

---

## 1. Milestone status

Legend: `TODO` · `IN PROGRESS` · `DONE` (verified in-console) · `BLOCKED`

| # | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Skeleton — metadata header, `TIC()`, `cls()`, "HELLO", scaffolding | DONE | Verified 2026-08-16: "HELLO" observed on screen via `tools/screendump.py` — 76 px of color 12 at x 105..133, y 64..68, rest of the screen color 0. 60.01 FPS on the host clock. Lint pass clean. |
| M1 | Player — movement, edge clamp, single bullet | TODO | |
| M2 | Fleet — 5 × 11 grid, stepped march, drop-and-reverse, waddle | TODO | |
| M3 | Combat — bullet kills, scoring, speed-up curve | TODO | |
| M4 | Threat — enemy fire, death, lives, game over | TODO | |
| M5 | Bunkers — cell-grid erosion, per-wave reset | TODO | |
| M6 | Mystery ship — spawn timing, traversal, bonus | TODO | |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | TODO | |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** M0 complete and verified in-console. Nothing is blocked; M1
(player movement and the single bullet) is next. Both remaining workflow gaps closed
this session — carts are packed with `pack.py`, and visual and frame-rate acceptance are
now checked by `tools/screendump.py` and `tools/fpscheck.py` rather than assumed.

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

Verified 2026-08-16, second pass:

| Component | State |
|---|---|
| Cartridge format | **This build is not PRO and refuses text carts.** `load game.lua` fails with "This version only supports binary .png or .tic cartridges. TIC-80 PRO is needed for text files." |
| Console Lua | **Lua 5.3**, from `trace(_VERSION)` in-console. Not the host `lua5.4`. See `docs/lua-notes.md` |
| Headless run | `--cli` works and prints console output to stdout, including `trace()`. Enough to verify load and runtime errors without a window |
| `lua5.3` host binary | not installed; available in the archive as `5.3.6-3` |
| Screenshot tooling | **None exists and none is needed.** `grim` fails ("compositor doesn't support wlr-screencopy-unstable-v1" — WSLg is not wlroots-based, so no Wayland tool will work), and no X11 tool is installed: `import`, `convert`, `xwd`, `ffmpeg`, `scrot`, `maim`, `xdotool` are all absent, as are Python `mss` and `PIL`. `sudo` needs a password, so an agent cannot install one. Superseded by reading VRAM directly — see below |

The documented run loop **does not work on this build**:

```bash
tic80 --fs=. --cmd="load game.lua & run"   # fails: text cart
```

What does work is packing the code into a minimal binary `.tic` first. A `.tic` is
4-byte-header chunks; a cart containing only a `CHUNK_CODE` (type 5) chunk loads and
runs. Header is `byte0 = bank<<5 | type`, `bytes1-2 = size little-endian`, `byte3`
reserved — https://github.com/nesbox/TIC-80/wiki/.tic-File-Format, read 2026-08-16:

```bash
python3 -c 'c=open("game.lua","rb").read(); open("game.tic","wb").write(
  bytes([5, len(c)&0xFF, (len(c)>>8)&0xFF, 0]) + c)'
tic80 --fs=. --cli --skip --cmd="load game.tic & run"
```

Confirmed working 2026-08-16 — printed `cart game.tic loaded!` and ran `BOOT()`. This
is the endorsed workflow as of the 2026-08-16 `pack.py` decision (§3). `.tic` is
gitignored.

Verified 2026-08-16, third pass — the verification harness in `tools/`:

| Check | State |
|---|---|
| Framebuffer readout | `python3 tools/screendump.py` works. VRAM is byte `0x00000`, 240 × 136 4-bit pixels, so `peek4(y * 240 + x)` is a pixel (`docs/tic80-ram.md`). Prints a palette histogram, bounding box, and the occupied region as ASCII |
| Frame rate | `python3 tools/fpscheck.py` works. **60.01 FPS** on the host wall clock, 60.00 by the console's `time()` |
| `trace()` under `--cli` | Output arrives with **no line break between calls** — a multi-line dump comes back as one flat stream, so parse by fixed width, not by lines |
| `exit()` | Returns to the TIC-80 console; it does **not** quit the process. A driving script must kill it, or it hangs until timeout |

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3). Note it checks 5.4 against a 5.3 console:

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

- **2026-08-16 — Verify visual acceptance by reading VRAM, not by screenshotting.**
  M0's acceptance is "text visible" and no capture tool works here (§2), which had left
  the milestone stuck a session. TIC-80's framebuffer is just RAM, so `tools/screendump.py`
  appends a probe to a copy of `game.lua`, wraps the cart's own `TIC()`, and dumps every
  pixel through `peek4`. It is *better* than a screenshot for this job — it reports exact
  coordinates and palette indices, which is what catches text drawn in an invisible
  color, and it runs headless in seconds. Recorded as `LINT-RULES.md` L051.
- **2026-08-16 — `tools/` is tracked, not part of gitignored `scratch/`.** The harness
  was written in `scratch/`, which would have thrown it away and made the next agent
  re-derive it — and every milestone M1–M8 has visual acceptance criteria that need it.
  It is scaffolding on the same footing as `pack.py`, so `AGENTS.md` §1's ban on build
  systems still stands; `scratch/` keeps the generated `.lua`/`.tic` intermediates.
- **2026-08-16 — Frame rate is measured windowed and cross-checked against the host
  clock.** Two traps, both of which would have produced a confident wrong answer.
  `--cli` is unthrottled, so its frame rate reflects host CPU, not console pacing. And
  the console's `time()` would be circular if TIC-80 derived it from the frame counter,
  which "60 FPS over 600 frames" could never detect. `tools/fpscheck.py` therefore runs
  windowed and takes a differential of two sample lengths against the host wall clock —
  differential because `exit()` does not end the process and startup adds an unknown
  constant, both of which cancel. The two clocks agree to 0.02 FPS. `LINT-RULES.md` L052.
- **2026-08-16 — Keep a `.lua`→`.tic` packer (`pack.py`) rather than building PRO from
  source.** User's call, given the console rejects text carts (§2). The TIC-80 README
  does sanction `cmake .. -DBUILD_PRO=On`, but that pulls the whole toolchain the
  2026-08-16 decision below avoided, to fix a problem four lines of Python already fix.
  `game.lua` stays the single tracked deliverable; `game.tic` is generated and
  gitignored. This is scaffolding, not a build system — `AGENTS.md` §1 still bars one.
  The footgun it introduces (running a stale `.tic` after editing the `.lua`) is
  checked as `LINT-RULES.md` L050 rather than left to memory.
- **2026-08-16 — Added `LINT-RULES.md` and wired it into `AGENTS.md` §1, §5, §6.**
  `AGENTS.md` stated conventions in prose, which meant every check depended on an agent
  remembering to look. The rules are now numbered, most carry a `grep`/`awk`/`luac`
  command, and §6 requires a clean pass before a milestone closes. §5 *Linting* asks
  each session to extend the file — add a check when a defect gets through, automate a
  **Read** rule when you find a way, and `RETIRED:` rather than delete. IDs are never
  reused or renumbered, since they get cited from here.
- **2026-08-16 — Rewrote `AGENTS.md` §5's comment rules; removed the banner-comment
  mandate.** §5 previously required sections "separated by banner comments", which
  invites `-- ===== CONSTANTS =====`. Sections are now one plain lowercase line
  (`-- constants`). The new §5 *Comments* subsection bans decorative characters,
  narration, notebook-style step-by-step prose, and TODO/NOTE tags, and restates that
  comments explain *why*. Enforced as `LINT-RULES.md` L030–L033.
- **2026-08-16 — `saveid` set in the M0 metadata header, ahead of `pmem` in M7.**
  `pmem` slots are keyed by `saveid`; picking it later would orphan any score already
  saved under the default. Free to set now, expensive to change later.
- **2026-08-16 — No state dispatcher in M0.** `MISSION.md` §4 requires `TIC()` to
  dispatch on state, but M0 has exactly one state and §5 forbids speculative
  abstraction. `STATE` and `game.state` exist; the dispatch table arrives with the
  second real state rather than as five empty stubs.
- **2026-08-16 — Centering uses `print`'s return value, not a hardcoded offset.**
  `print` reports width only by drawing, so `print_centered` draws once at `y = -FONT_H`
  to measure and again in place. Costs one offscreen draw per frame; keeps the layout
  correct if the string changes.
- **2026-08-16 — Corrected §1's repo root** to `/home/tic-80/stauros-invaders`,
  resolving the §6 question. It was wrong in a public repo.
- **2026-08-16 — Added `AGENTS.md` §3 *Keeping `PROGRESS.md` current* to govern this
  file.** `AGENTS.md` referenced `PROGRESS.md` in six places but never defined its
  structure or when to write to it, so "keep it updated" was unenforceable and the six
  section names here were undocumented. That subsection now maps each section to its
  write trigger and states the `DONE`-means-observed and never-delete-a-resolved-question
  rules. Keep the section list here and the table there in sync if either changes.
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

- `docs/tic80-api.md` — created 2026-08-16. Verified from the wiki, with URLs and dates:
  `cls`, `print`, `trace`, the `TIC()` and `BOOT()` callbacks, the SWEETIE-16 palette,
  and the cartridge metadata tags. These are every API call `game.lua` currently makes —
  cross-checked mechanically via `LINT-RULES.md` L011, which lists the cart's globals
  from bytecode.
- `docs/lua-notes.md` — created 2026-08-16. Console reports **Lua 5.3**; 5.4-only forms
  (`<close>`, `<const>`, `warn`, `coroutine.close`) will not load, and host `luac5.4`
  will not catch them because it is a superset.
- `docs/tic80-ram.md` — created 2026-08-16, when the harness started reading VRAM.
  Records the screen region only: byte `0x00000`, 240 × 136 4-bit pixels, two per byte
  low-nibble-first, so `peek4(y * 240 + x)` is a pixel. Notes that `vbank(1)` would
  switch banks under anything reading VRAM, and that `pmem`'s region at `0x14004` gets
  documented when M7 needs it, not before.
- `peek4`, `exit`, and `time` added to `docs/tic80-api.md` 2026-08-16. They are used by
  `tools/`, not by `game.lua`, but `AGENTS.md` §4.1 is about the project and each has a
  gotcha worth having written down: `peek4` addresses by *nibble*, not byte; `exit()`
  runs the rest of the current `TIC()` and returns to the console instead of quitting;
  `time()` is wall-clock from cart start, confirmed against the host clock.
- Two `print` gotchas recorded: its default color 15 is dark navy and invisible on the
  black the game clears to, and it returns the drawn width, which is how text gets
  centered.

---

## 5. Known bugs

None — there is no code yet.

---

## 6. OPEN QUESTIONS

Per `AGENTS.md` §4.5: state the question, implement around it under a clearly stated
assumption, and record the assumption here. Mark answered ones `RESOLVED:` with the
answer and its source; do not delete them.

- **RESOLVED: Does "HELLO" actually render?** **Yes.** Source: `tools/screendump.py`,
  run 2026-08-16, reading the framebuffer through `peek4`. The screen is 32,564 px of
  color 0 and 76 px of color 12, forming legible "HELLO" glyphs in a bounding box of
  x 105..133, y 64..68 — margins 105 left and 106 right, the one-pixel asymmetry being
  the expected `math.floor` in `print_centered`. The answer turned out not to need a
  screenshot tool at all (§3), so the sub-question of which one to install is moot.
- **RESOLVED: Does the cart hold 60 FPS?** **Yes — 60.01 FPS**, host wall clock, via
  `tools/fpscheck.py` on 2026-08-16. This was never written down as an open question but
  was just as unverified as the one above: M0's acceptance criterion says "60 FPS" and
  nothing had measured it.
- **RESOLVED: How should text carts be run, given this build is not PRO?** With
  `pack.py`, per the user's decision on 2026-08-16 (§3). Building PRO from source
  (`cmake .. -DBUILD_PRO=On`, sanctioned by the TIC-80 README) and buying PRO were the
  alternatives considered.
- **RESOLVED: Does `AGENTS.md` §1's stated repo root need correcting?** Yes — corrected
  to `/home/tic-80/stauros-invaders` on 2026-08-16.
- **RESOLVED: Which Lua version does TIC-80 1.1.2837 embed?** **Lua 5.3.** Source:
  `trace(_VERSION)` run in-console 2026-08-16, recorded in `docs/lua-notes.md`. Integer
  division, `goto`, and bitwise operators are available; 5.4-only syntax is not.
