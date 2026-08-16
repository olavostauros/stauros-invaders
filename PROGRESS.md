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
| M0 | Skeleton — metadata header, `TIC()`, `cls()`, "HELLO", scaffolding | IN PROGRESS | Cart written, lint-clean, loads and runs headless with no errors. Not `DONE`: the screen has not been *seen*. See §6. |
| M1 | Player — movement, edge clamp, single bullet | TODO | |
| M2 | Fleet — 5 × 11 grid, stepped march, drop-and-reverse, waddle | TODO | |
| M3 | Combat — bullet kills, scoring, speed-up curve | TODO | |
| M4 | Threat — enemy fire, death, lives, game over | TODO | |
| M5 | Bunkers — cell-grid erosion, per-wave reset | TODO | |
| M6 | Mystery ship — spawn timing, traversal, bonus | TODO | |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | TODO | |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** M0 code complete and running. Blocked on one workflow decision —
this TIC-80 build cannot load `.lua` text carts (§2), so how carts get run needs
settling before M1.

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
| Screenshot tooling | `grim` installed 2026-08-16 but **does not work here** — it fails with "compositor doesn't support wlr-screencopy-unstable-v1". WSLg's compositor is not wlroots-based, so no Wayland screenshot tool will work. Capture must go through XWayland (`DISPLAY=:0`) with an X11 tool instead — `import -window` from `imagemagick`, since rootless XWayland has no useful root window to grab |

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
is a stopgap pending the §6 decision, not an endorsed workflow. `.tic` is gitignored.

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3). Note it checks 5.4 against a 5.3 console:

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

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
- `docs/tic80-ram.md` — not created. Nothing pokes RAM yet (`AGENTS.md` §4.4 records
  only what is used).
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

- **Does "HELLO" actually render?** M0's acceptance is visual, and no screenshot tool
  exists in this environment (§2), so no agent has seen the screen. The cart is
  confirmed to load and run without error headlessly, which is strictly less than the
  acceptance criterion. **Assumption:** it draws as written; M0 stays `IN PROGRESS`
  until the screen is captured. `grim` was installed for this and turned out not to work
  on WSLg (§2); an X11 tool is needed instead. Note `sudo` requires a password here, so
  an agent cannot install packages unattended — ask the user.
- **RESOLVED: How should text carts be run, given this build is not PRO?** With
  `pack.py`, per the user's decision on 2026-08-16 (§3). Building PRO from source
  (`cmake .. -DBUILD_PRO=On`, sanctioned by the TIC-80 README) and buying PRO were the
  alternatives considered.
- **RESOLVED: Does `AGENTS.md` §1's stated repo root need correcting?** Yes — corrected
  to `/home/tic-80/stauros-invaders` on 2026-08-16.
- **RESOLVED: Which Lua version does TIC-80 1.1.2837 embed?** **Lua 5.3.** Source:
  `trace(_VERSION)` run in-console 2026-08-16, recorded in `docs/lua-notes.md`. Integer
  division, `goto`, and bitwise operators are available; 5.4-only syntax is not.
