# AGENTS.md

Operating rules for any agent working in this repository.

Read this file **and** `MISSION.md` before touching code. `AGENTS.md` says *how* to work; `MISSION.md` says *what* to build.

---

## 1. Project at a glance

| | |
|---|---|
| Target platform | TIC-80 fantasy console (version 1.x) |
| Language | Lua (TIC-80's embedded interpreter) |
| Deliverable | `game.lua` — a single, runnable TIC-80 cartridge |
| Genre | Space Invaders clone (see `MISSION.md`) |
| Repo root | `/home/tic-80/stauros-invaders` |

### Directory layout

```
game.lua        the cartridge — the only file TIC-80 loads
pack.py         packs game.lua into a binary game.tic (see §3; non-PRO console)
README.md       required tooling and how to build, run, and screenshot the cart
MISSION.md      game design spec + milestone plan
AGENTS.md       this file
LINT-RULES.md   lint rules for game.lua and the commands that check them (see §5)
PROGRESS.md     running log: milestone status, decisions, open questions (see §3)
docs/           local cache of TIC-80 / Lua reference material (see §4)
tools/          verification harness — reads the framebuffer and the frame rate (see §6)
scratch/        throwaway experiments and generated intermediates; never referenced by game.lua
```

Do not create build systems, package manifests, transpilers, or `src/` module trees
without an explicit instruction to. TIC-80 loads exactly one file and has no `require`.

---

## 2. Hard constraints of the target

These are not style preferences. Violating any of them produces a cartridge that
does not run.

**Runtime**
- The console calls `TIC()` once per frame at **60 FPS**. All game logic and all
  drawing happen inside that call. There is no separate update/render callback.
- `BOOT()` (if defined) runs once before the first `TIC()`. Use it for one-time init.
- A frame that overruns its budget drops frames silently. Keep per-frame work bounded;
  never allocate large tables inside `TIC()`.
- There is no `main()`, no event loop you control, and no way to block. Never write
  `while true do ... end` around game logic and never busy-wait.

**Display**
- Screen is **240 × 136 pixels**, 16 colors, palette indices `0..15`.
- The default palette is SWEETIE-16. Refer to colors by index, and define named
  constants for the ones the game uses rather than sprinkling magic numbers.
- Sprites are 8 × 8. `spr()` can draw multi-sprite blocks via its `w`/`h` arguments,
  which consume the sprite sheet **left-to-right, top-to-bottom** from the given id.

**Language**
- Lua as embedded by TIC-80 — a **subset** of stock Lua. Assume unavailable until
  proven otherwise: `require`, `io.*`, `os.execute`, file access, `package`, sockets,
  coroutine-based schedulers you did not write yourself.
- Confirm the interpreter version in-console with `trace(_VERSION)` before relying on
  any version-specific feature (integer division, `goto`, `<close>`, `math.type`,
  bitwise operators). Do not assume from memory.
- Globals are shared across frames and persist. Prefer `local` for everything;
  hoist state into a small number of explicit global tables.
- Persistent storage is only `pmem(index, value)` — 32-bit integer slots. There is no
  filesystem.

**Cartridge**
- `game.lua` must start with the TIC-80 metadata header comment block, including
  `-- script: lua`. Without it the console may refuse the file or pick the wrong
  interpreter. Preserve this block through every edit.
- Code size in a cartridge is capped (on the order of 64 KB). If the file approaches
  that, report it — do not silently minify.

---

## 3. How to work

1. **Read `MISSION.md`, then `PROGRESS.md`.** Pick up at the first incomplete milestone.
   Do not skip ahead; each milestone leaves the game in a runnable state.
2. **One milestone per working session.** Implement it fully, verify it runs, update
   `PROGRESS.md` per *Keeping `PROGRESS.md` current* below, then stop and report.
3. **Keep `game.lua` runnable at all times.** Never commit or hand back a cartridge
   that errors on load. A half-implemented feature behind a flag is acceptable;
   a syntax error is not.
4. **Verify before claiming.** "Implemented" means you loaded the cart and saw the
   behavior. If you could not run it, say so explicitly in your report — do not
   describe untested code as working.
5. **Report honestly.** If a milestone is partly blocked, finish everything that is
   not blocked, then state plainly what is missing and why.

### Keeping `PROGRESS.md` current

`PROGRESS.md` is the authoritative record of where the project stands. The code says
what the game does; `PROGRESS.md` says what is finished, what was decided and why, and
what is still unknown. A session that changes the project without updating it has left
the next agent to re-derive all of that from a diff.

It has six sections. Write to the right one:

| Section | Holds | Write when |
|---|---|---|
| 1. Milestone status | The M0–M8 table and a one-line "current position" | A milestone starts, finishes, or blocks |
| 2. Environment | Verified tool versions, the run loop, display/audio state | A tool is installed, upgraded, or found broken |
| 3. Decisions | Newest-first log of choices **and their rationale** | A judgment call is made that a later agent could otherwise second-guess |
| 4. API documentation status | Which TIC-80 functions are verified in `docs/`, and the console's Lua version | New signatures are recorded per §4.1 |
| 5. Known bugs | Reproducible defects not yet fixed | A bug is found — including one you caused and chose not to fix yet |
| 6. OPEN QUESTIONS | Unresolved unknowns and the assumption used to work around each | Per §4.5, whenever you proceed on an assumption |

Rules for the file:

- **Update it as you go, not only at milestone end.** Decisions and open questions are
  written when they happen; a decision reconstructed hours later loses its reasoning.
- **A milestone is `DONE` only when it was observed running in the console** (rule 4
  above, and §6). Untested code is `IN PROGRESS`, never `DONE`. If you could not run TIC-80, say
  so in the milestone's Notes column rather than upgrading its status.
- **Never delete an answered open question.** Mark it `RESOLVED:` with the answer and
  its source, per §4.5. The record of what was once uncertain has value.
- **Dates are absolute** (`2026-08-16`), never "today" or "last session".
- Keep entries short. This is a log, not a design document — reasoning that belongs in
  the spec goes to `MISSION.md`, and API facts go to `docs/`.

### Running the game

TIC-80 1.1.2837 is at `/usr/bin/tic80`. It is **not the PRO build**, and non-PRO builds
refuse text cartridges — `load game.lua` fails outright. The code must be packed into a
binary `.tic` first:

```bash
python3 pack.py                                        # game.lua -> game.tic
tic80 --fs=. --cli --skip --cmd="load game.tic & run"  # headless; console output only
tic80 --fs=. --skip --cmd="load game.tic & run"        # windowed, needs WSLg
```

**Always re-run `pack.py` after editing `game.lua`.** Running a stale `game.tic` shows
you the previous build and produces bug reports about code you already fixed. This is
`LINT-RULES.md` L050.

`game.lua` remains the only tracked deliverable; `game.tic` is generated and gitignored.
`pack.py` exists solely because of the PRO restriction — it is not a build system, and
§1's prohibition on adding one still stands.

Verify flags against `tic80 --help` for the installed build; they have changed across
versions. If the console cannot be launched at all, fall back to a **syntax check
only** — `luac5.4 -p game.lua` — and label the result *syntax verified, behavior
unverified*. A syntax check is not a test, and `luac5.4` is a version ahead of the
console's Lua 5.3 (`docs/lua-notes.md`).

Headless `--cli` runs print `trace()` output to stdout, which is enough to confirm a
cart loads and runs without errors. It is **not** enough for any acceptance criterion
about what is on screen, and not enough for frame rate either.

### Verifying what is on screen

No screenshot tool works here — `grim` needs a wlroots compositor and WSLg is not one,
no X11 capture tool is installed, and `sudo` needs a password an agent does not have.
Read the framebuffer out of RAM instead. Both tools append a probe to a *copy* of
`game.lua` and wrap the cart's own `TIC()`, so the code under test runs exactly as
committed (`LINT-RULES.md` L053):

```bash
python3 tools/screendump.py    # every pixel via peek4: histogram, bounding box, ASCII
python3 tools/fpscheck.py      # frame rate, windowed, cross-checked against the host clock
python3 tools/inputsim.py      # scripted gamepad input, checked against the game's state
```

Never conclude "it renders" from a clean headless run — `print` with a defaulted color
draws invisibly and errors nothing (`LINT-RULES.md` L008, L051). Never measure frame rate
under `--cli`; it is unthrottled and the number is meaningless (L052).

### Verifying what the game does

No key can be pressed here, so the gamepad is written straight to RAM at `0x0FF80` and
the game's own state is read back per frame. Every milestone's acceptance criteria are
about behavior under input; each gets a scenario in `tools/inputsim.py` (`LINT-RULES.md`
L054). Note that `btnp` cannot be simulated this way and the probe substitutes its own —
the limitation is documented in `docs/tic80-api.md` and must be restated, not forgotten,
whenever a press-versus-hold criterion is closed.

### Debugging

- `trace(value, color)` prints to the TIC-80 console. Use it liberally while
  developing; strip or gate debug traces behind a `DEBUG` flag before finishing a
  milestone.
- A frozen or blank screen is almost always an error thrown inside `TIC()` — check
  the console output first.
- When a behavior is wrong, reproduce it with the smallest possible cart in
  `scratch/` before editing `game.lua`.

---

## 4. Documentation rules

These rules exist because TIC-80's API is small, idiosyncratic, and easy to
misremember. Argument **order** in particular differs from most engines, and a wrong
argument usually fails silently rather than erroring.

### 4.1 The rule of first use

**Before the first use of any TIC-80 API function in this project, look up its
signature in the official documentation and record it in `docs/tic80-api.md`.**

Applies to every function without exception, including ones that feel obvious:
`spr`, `btn`, `btnp`, `print`, `rect`, `rectb`, `cls`, `sfx`, `music`, `map`, `mget`,
`mset`, `pix`, `line`, `circ`, `tri`, `ttri`, `peek`, `poke`, `pmem`, `fget`, `fset`,
`time`, `trace`, `vbank`, `sync`, `exit`, `reset`, `key`, `keyp`, `mouse`, `font`,
`clip`, `memcpy`, `memset`.

Record for each: exact name, full parameter list **in order**, which parameters are
optional and their defaults, the return value, and one line on any surprising
behavior. Cite the URL you read it from.

### 4.2 Sources of truth, in priority order

**TIC-80**
1. The official wiki — `https://github.com/nesbox/TIC-80/wiki` — and specifically the
   `API` and `RAM` pages. This is authoritative.
2. `https://tic80.com/learn` for tutorials and worked examples.
3. The TIC-80 source repository, when the wiki is ambiguous about behavior.
4. The console's own `help` command, if a live TIC-80 is available.

**Lua**
1. The reference manual for the version the console actually reports —
   `https://www.lua.org/manual/5.4/` (adjust the version to match `_VERSION`).
2. *Programming in Lua* for idiom questions.

Nothing else is a source of truth. Blog posts, forum answers, LLM recall, and
other people's carts are **hypotheses**, not documentation. If one suggests an
approach, confirm it against the wiki or manual before it goes into `game.lua`.

### 4.3 Anti-hallucination rules

- **Never invent an API.** If a function you want does not appear in the wiki API
  page, it does not exist. Build it out of what does exist.
- **Never guess argument order or optional-argument positions.** Look it up. Where a
  parameter is skipped, be explicit about what the default is — TIC-80 signatures use
  positional optionals, so a missing middle argument shifts everything after it.
- **Never assume a stock Lua library is present.** Check §2 and confirm in-console.
- **Never assume version parity.** TIC-80 renamed and removed functions across
  versions (e.g. the `textri` → `ttri` rename, the removal of `OVR`). If you find
  advice that predates 1.0, verify it still applies before using it.
- If documentation and observed behavior disagree, **the running console wins.**
  Record the discrepancy in `docs/tic80-api.md` with a `DISCREPANCY:` marker.

### 4.4 Caching

Web access may be unavailable in a later session. When you fetch documentation,
write the relevant portion to `docs/` immediately:

```
docs/tic80-api.md     verified signatures + notes (the important one)
docs/tic80-ram.md     memory map addresses, only those actually used
docs/lua-notes.md     TIC-80-specific Lua deviations you confirmed
```

Each entry carries the source URL and the date you read it. Before fetching anything,
check `docs/` first — a verified local note beats a re-fetch.

### 4.5 Uncertainty

If you cannot verify something and cannot proceed without it, write down the specific
question, implement the rest of the milestone around it under a clearly stated
assumption, and flag it in `PROGRESS.md` under `OPEN QUESTIONS` (§3). Do not stall the
whole milestone on one unknown, and do not paper over the gap with a confident guess.

---

## 5. Code conventions

- **Structure `game.lua` in labeled sections**, in this order: metadata header →
  constants → state → helpers → entity update functions → entity draw functions →
  collision → game-state machine → `TIC()` → `BOOT()`. Separate them with a single
  plain comment line naming the section, lowercase — `-- constants`, nothing more.
- **`local` by default.** Reach for a global only for the top-level state tables, and
  keep those few and named.
- **Named constants, not magic numbers.** Screen bounds, speeds, colors, sprite ids,
  and score values all get names at the top of the file.
- **Data-driven over hardcoded.** Enemy rows, wave timings, and point values belong in
  tables you can tune, not scattered through logic.
- **Pure update functions where practical.** `update_x(entity, dt)` mutating one entity
  is fine; a function that touches four unrelated globals is not.
- **No dead code, no commented-out blocks, no speculative abstraction.** Delete it;
  it is recoverable from history.
- Indent with 2 spaces. Keep lines under 100 characters.

### Comments

`game.lua` is a program, not a notebook. A comment earns its place only by saying
something the code cannot say for itself.

- **Explain *why*, never *what*.** A comment justifies a choice: why 55 frames, why a
  formula is shaped oddly, why an edge case exists. If it restates the line below it,
  delete it.
- **No narration.** No running commentary ("now we loop over the invaders", "first,
  clear the screen"), no step numbering, no explanations pitched at someone learning
  Lua. Nobody is reading over your shoulder.
- **No decorative characters.** A comment is plain prose after `--`. No `=====`,
  `-----`, `*****`, `#####`, box-drawing characters, ASCII art, centered or padded
  text, and no ALL-CAPS titles. A section label is one line: `-- constants`.
- **No meta-commentary.** Comments never address the user, announce what changed, mark
  work finished, cite a milestone or session, or carry TODO/FIXME/NOTE/HACK tags.
  Status lives in `PROGRESS.md`; history lives in git.
- **Keep them short.** One line where one line does. A comment longer than the code it
  explains means the code needs the work, not the comment.

### Linting

`LINT-RULES.md` turns this section and §2 into numbered, mostly automated checks. Run
the full pass before closing a milestone (§6); it is `grep`, `awk`, and `luac5.4`, so it
costs seconds.

**Improve the rules as you go — this is part of the job, not overhead.** The file is a
record of mistakes worth not repeating, and it only earns that if it grows:

- When a defect reaches the console that a check could have caught, add the check.
- When a review catches a style slip, add the rule rather than fixing the one instance.
- When you find a way to automate a rule currently marked **Read**, automate it and move
  its command into *Running the pass*.
- When a rule proves wrong or obsolete, mark it `RETIRED:` with the reason and date.
  Never delete a rule, never renumber one, never reuse an ID — they are cited elsewhere.

Every added rule carries its *why* and the date and trigger that produced it. A rule
whose reason is lost gets argued away the first time it is inconvenient. Log notable
additions in `PROGRESS.md` §3 alongside the decision that prompted them.

---

## 6. Definition of done, per milestone

A milestone is complete when all of the following hold:

- [ ] `game.lua` loads in TIC-80 with no console errors.
- [ ] The milestone's acceptance criteria in `MISSION.md` are observably met — for
      anything visual, observed with `tools/screendump.py`, not inferred from a clean run.
- [ ] The `LINT-RULES.md` pass runs clean, and any rule the milestone taught you is
      written down (§5 *Linting*).
- [ ] Every new TIC-80 API call used is recorded in `docs/tic80-api.md`.
- [ ] No debug `trace()` calls fire during normal play.
- [ ] Frame rate holds at 60 with the milestone's worst-case entity count on screen,
      measured windowed with `tools/fpscheck.py`.
- [ ] `PROGRESS.md` updated per §3: milestone status moved to `DONE`, any decisions
      and their rationale logged, open questions carried forward or marked `RESOLVED:`.

---

## 7. Scope discipline

Build what `MISSION.md` specifies. Do not add menus, shaders, particle systems,
alternate game modes, or engine abstractions that the spec does not call for.

If you believe the spec is wrong, say so in one or two sentences, then implement it
as written and note the concern in `PROGRESS.md` under Decisions (§3). Scope changes
are the user's call.
