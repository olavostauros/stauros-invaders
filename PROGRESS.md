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
| M1 | Player — movement, edge clamp, single bullet | DONE | Verified 2026-08-16 with `tools/inputsim.py`: 1 px/frame both ways, clamped at x 0 and 232, one bullet per press, 6 presses during flight ignored, bullet rises 2 px/frame and frees its slot on frame 60. Ship and bullet observed on screen via `tools/screendump.py`; 60.00 FPS moving and firing. Lint pass clean. The `btnp` caveat below is the one gap. |
| M2 | Fleet — 5 × 11 grid, stepped march, drop-and-reverse, waddle | DONE | Verified 2026-08-17 with `tools/inputsim.py`: 56 steps in 3,100 frames, every one on a multiple of 55, each a 2 px move along the current direction, the waddle toggling on all 56; two drop-and-reverses, at x 72 and x 0, each +6 px in y with no sideways move. Grid observed via `tools/screendump.py` — 55 invaders at x 36..203, y 20..67, three distinct shapes across the five rows — and again at frame 1050, flush right at x 72..239 and one row lower at y 26. 60.00 FPS with the full fleet, moving and firing. Lint pass clean. |
| M3 | Combat — bullet kills, scoring, speed-up curve | TODO | |
| M4 | Threat — enemy fire, death, lives, game over | TODO | |
| M5 | Bunkers — cell-grid erosion, per-wave reset | TODO | |
| M6 | Mystery ship — spawn timing, traversal, bonus | TODO | |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | TODO | |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** M2 complete and verified in-console. Nothing is blocked; M3
(bullet-versus-invader collision, scoring, and the step interval shrinking with the
living count) is next, and the fleet it inherits is already built for it: `game.fleet`
carries an `alive[row][col]` grid, edge detection reads the living columns rather than
the grid's, and `FLEET_STEP_FRAMES` is the one constant the speed-up curve replaces.
M3 must also decide what happens when the last invader dies — `live_columns()` returns
nil for an empty fleet and `step_fleet()` would error on it, which cannot happen while
nothing can die.

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

Verified 2026-08-16, fourth pass — input simulation:

| Check | State |
|---|---|
| Gamepad via RAM | Works for `btn`. `poke(0x0FF80, mask)` inside `TIC()` is visible to `btn()` on the same frame; the console rewrites the byte each frame, so the probe writes it every frame including zeros |
| `btnp` via RAM | **Does not work.** A poked hold reads as a fresh press on every frame — `btnp(4)` true on all nine frames of a held mask. The previous-state snapshot comes from the real input device, not RAM. `tools/inputsim.py` keeps a standing scenario watching this, so a console upgrade that fixes it gets noticed rather than assumed |
| Scripted scenarios | `python3 tools/inputsim.py` runs seven scenarios against the game's own state and reports pass/fail. `--hold` also added to `screendump.py` and `fpscheck.py` |
| Keystroke injection | Still impossible. WSLg takes input from the Windows side; `xdotool`/`ydotool`/`wtype` are absent and `/dev/uinput` would not reach the compositor anyway |

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3). Note it checks 5.4 against a 5.3 console:

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

- **2026-08-17 — The fleet turns on the step that would leave the screen, rather than on
  the one after.** `MISSION.md` §3 says the fleet drops and reverses when a live invader
  touches an edge, which leaves open whether the touching step also moves. It does not:
  the step whose horizontal move would cross the edge becomes the drop instead. That
  guarantees the fleet is flush against the edge when it turns — measured at x 0 and
  x 72, the rightmost invader ending on x 239 — where moving first and turning later
  would leave a ragged 0–1 px margin that varies with the living columns.
- **2026-08-17 — Edge detection scans the living columns, and `alive` exists before
  anything can kill.** `MISSION.md` §3 defines the turn by "any *live* invader", so
  bounding the fleet by columns 1 and 11 would be wrong the moment M3 lands and would
  have to be rewritten rather than extended. `game.fleet.alive[row][col]` is a plain
  boolean grid, not a table per invader — 55 tables would buy nothing M2 or M3 needs, and
  `LINT-RULES.md` L009 keeps allocation out of the frame path anyway. The one thing
  deliberately left out is a guard for an *empty* fleet: `live_columns()` returns nil and
  `step_fleet()` would error, which is unreachable while nothing can die, and M3 has to
  handle the empty fleet as a wave-clear rather than as a nil check.
- **2026-08-17 — The step interval is a constant 55 in M2; the curve is M3's.**
  `MISSION.md` §3 wants N driven by the living count, and §8 puts that in M3 with the
  kills that make it observable. Implemented here it would be a formula over a number
  that never changes — untestable, and the speculative abstraction `AGENTS.md` §5 bans.
  55 is the arcade's own value: the original moved one invader per frame, so a full fleet
  stepped once every 55 frames.
- **2026-08-17 — Fleet layout: 16 × 10 px pitch, starting at (36, 20), dropping 6 px.**
  `MISSION.md` §2 gives the coordinates as targets to tune and asks that the horizontal
  travel fit and the bottom row have room to descend. 11 columns on a 16 px pitch span
  168 px, leaving 72 px of travel and centring the fleet at x 36. A 10 px row pitch puts
  the five rows in y 20..67 — clear of the HUD band and the UFO lane — and a 6 px drop
  gives ten drops from the bottom row to the player's row at y 120.
- **2026-08-17 — All invaders drawn in one color (white).** `MISSION.md` §3 asks for
  three visual types, not three colors, and the 1978 original was monochrome behind a
  colored overlay. The three shapes read apart on screen at 8 × 8, confirmed in the
  framebuffer dump, so color is spare — it stays available for M4's explosions and M6's
  mystery ship, where it will mean something.
- **2026-08-16 — Simulate input by writing the gamepad byte in RAM, and substitute
  `btnp` in the probe.** Every milestone from M1 on has acceptance criteria about
  behavior under input, and nothing here can press a key (§2). GAMEPADS is 4 bytes at
  `0x0FF80`, so `btn` is drivable for real. `btnp` is not — the console snapshots the
  previous frame from the real input device, so a poked hold looks like a fresh press
  every frame, which was measured rather than assumed. `tools/input-probe.lua` therefore
  overrides the global `btnp` with an edge detector over the mask it wrote. This tests
  `game.lua` unmodified under the semantics the wiki documents, and the substitution is
  stated everywhere it matters rather than buried: `LINT-RULES.md` L054,
  `docs/tic80-api.md`, §6 below. The alternative — declaring the criterion met by
  reading the source — is what L054 exists to forbid.
- **2026-08-16 — The sprite sheet lives in `game.lua` and is blitted into tile RAM at
  boot.** `pack.py` writes a `CHUNK_CODE` chunk and nothing else, so the cart ships no
  sprite data at all. Teaching `pack.py` to emit a `CHUNK_TILES` from a separate binary
  would have made the sheet a second deliverable that `AGENTS.md` §1 says should not
  exist, and editing sprites would have meant launching the console's editor. Instead
  `SPRITE_SHEET` holds pixel rows as strings and `BOOT()` pokes them in — 64 `poke4`
  calls per sprite, once, never in the frame path (L009). Sprites stay diffable text and
  M2's six invader frames are new table entries, not a new pipeline. Recorded as
  `LINT-RULES.md` L016, because drawing an unblitted id fails silently.
- **2026-08-16 — The ship is 7 px wide inside its 8 px tile.** An 8-wide symmetric shape
  has no centre column, so the muzzle and the 1 px bullet could not agree; at 7 wide the
  barrel sits on column 3 and the bullet leaves from exactly there. Confirmed on screen:
  bullet x 119 with the ship at x 116.
- **2026-08-16 — `--hold` added to `screendump.py` and `fpscheck.py`.** Both were
  measuring an idle cart, which for a game about moving and shooting is the one frame
  that proves least. `AGENTS.md` §6 asks for the worst-case entity count; now it can be
  asked for. M1 measured 60.00 FPS with right-plus-fire held, against 60.03 idle.
- **2026-08-16 — M0's empty section labels and `DEBUG` flag removed.** `-- collision`
  and `-- game state machine` over nothing are placeholders for structure that does not
  exist, which is the speculative abstraction `AGENTS.md` §5 bans; L014 fixes the order
  sections appear in, not that all of them must. The `DEBUG` flag went with its only
  user, the `_VERSION` trace, whose question is now answered in `docs/lua-notes.md`.
  Both come back the moment something needs them. `LINT-RULES.md` L015, amended.
- **2026-08-16 — Still no state dispatcher, and `game.state` now starts at `PLAYING`.**
  Same reasoning as M0's decision below: M1 has exactly one live state and five empty
  stubs would be worse than none. `PLAYING` is simply what the cart now does. The
  dispatch table arrives with the second real state, which is M4 or M7.
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
- M1 added, 2026-08-16, all verified from the wiki with URLs and dates: `spr`, `rect`,
  `btn`, `btnp`, the player-1 button id table (left 2, right 3, A 4, confirming
  `MISSION.md` §7), and `poke`/`poke4`. `print` and `print_centered` left the cart with
  M0's placeholder text and will be re-verified when the HUD needs them in M7.
- `docs/tic80-ram.md` gained the two regions M1 touches: TILES at `0x4000` and SPRITES
  at `0x6000` (32 bytes per 8 × 8 tile, low nibble the left pixel, so `poke4` sees a
  tile as 64 nibbles in row-major order), and GAMEPADS at `0x0FF80`.
- `docs/lua-notes.md` stdlib list extended: `ipairs`, `tostring`, `string` (including
  the `s:sub()` method form) and `table` all confirmed running in-console.
- M2 added no TIC-80 call, 2026-08-17. Checked mechanically rather than asserted: the
  L011 `_ENV` list is unchanged from M1 — `BOOT`, `TIC`, `btn`, `btnp`, `cls`, `game`,
  `ipairs`, `math`, `poke4`, `rect`, `spr` — so `docs/tic80-api.md` needed no new entry.
  The fleet is 55 more `spr` calls of a signature already recorded.
- The `btnp` entry carries a `DISCREPANCY:` marker per `AGENTS.md` §4.3 — not between
  the docs and the console, but between the console and RAM: `btnp` ignores writes to
  the GAMEPADS region. It is the reason `tools/inputsim.py` supplies its own.

---

## 5. Known bugs

None reproducible as of 2026-08-17. Every M1 and M2 scenario in `tools/inputsim.py`
passes, and both framebuffer dumps match the milestone's acceptance criteria.

---

## 6. OPEN QUESTIONS

Per `AGENTS.md` §4.5: state the question, implement around it under a clearly stated
assumption, and record the assumption here. Mark answered ones `RESOLVED:` with the
answer and its source; do not delete them.

- **OPEN: Does the console's own `btnp` hold to one shot per press, under a real
  finger?** Assumed **yes**, on the wiki's documented semantics — `btnp(id)` with `hold`
  and `period` omitted returns true only on the frame a button becomes pressed, and
  `game.lua` omits both deliberately. The assumption cannot be closed here: the gamepad
  RAM that drives `btn` is invisible to `btnp` (§2), so `tools/inputsim.py` substitutes
  an edge-detecting `btnp` of its own. What *is* measured against the console is the
  stronger invariant — six presses during a bullet's flight produced one bullet — so the
  worst case if the assumption is wrong is a stream at the fire rate, never two bullets
  at once. Closable in seconds by a human holding the fire key on a windowed run;
  otherwise it closes when a keystroke-injection route is found.
- **OPEN: Is a 55-frame step at 55 alive the right opening pace?** It is `MISSION.md`
  §3's suggested value and the arcade's own, so it is the best available answer, but at
  2 px every 0.9 s the fleet takes ~33 s to cross an empty screen and the opening minute
  is slow. §3 says to tune by playing, and nothing here can play; the constant is
  `FLEET_STEP_FRAMES`. Revisit when M3's curve makes the *shape* of the ramp visible,
  since the two tune together.
- **OPEN: Is 1 px/frame the right ship speed, and 2 px/frame the right bullet?** They
  are `MISSION.md` §3's suggested values, implemented as named constants
  (`PLAYER_SPEED`, `BULLET_SPEED`) so tuning is a one-line change. §3 says to tune by
  playing, which no tool here can do — carried until someone plays it, and worth
  revisiting once the fleet in M2 gives the ship something to aim at.
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
