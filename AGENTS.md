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
| Repo root | `/home/tic-80/game` |

### Directory layout

```
game.lua        the cartridge — the only file TIC-80 loads
MISSION.md      game design spec + milestone plan
AGENTS.md       this file
PROGRESS.md     running log: milestone status, decisions, known bugs
docs/           local cache of TIC-80 / Lua reference material (see §4)
scratch/        throwaway experiments; never referenced by game.lua
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
   `PROGRESS.md`, then stop and report.
3. **Keep `game.lua` runnable at all times.** Never commit or hand back a cartridge
   that errors on load. A half-implemented feature behind a flag is acceptable;
   a syntax error is not.
4. **Verify before claiming.** "Implemented" means you loaded the cart and saw the
   behavior. If you could not run it, say so explicitly in your report — do not
   describe untested code as working.
5. **Report honestly.** If a milestone is partly blocked, finish everything that is
   not blocked, then state plainly what is missing and why.

### Running the game

TIC-80 is **not currently installed in this environment**. Before your first run,
check with `command -v tic80` and report the result rather than guessing.

Once available, the standard loop is:

```bash
tic80 --fs=. --cmd="load game.lua & run"
```

Verify the exact flags for the installed build with `tic80 --help`; CLI flags have
changed across TIC-80 versions. If the console cannot be launched (no display, not
installed), fall back to a **syntax check only** — `luac -p game.lua` or
`lua -e "assert(loadfile('game.lua'))"` — and label the result as *syntax verified,
behavior unverified*. A syntax check is not a test.

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
assumption, and flag it in `PROGRESS.md` under `OPEN QUESTIONS`. Do not stall the
whole milestone on one unknown, and do not paper over the gap with a confident guess.

---

## 5. Code conventions

- **Structure `game.lua` in labeled sections**, in this order, separated by banner
  comments: metadata header → constants → state → helpers → entity update functions →
  entity draw functions → collision → game-state machine → `TIC()` → `BOOT()`.
- **`local` by default.** Reach for a global only for the top-level state tables, and
  keep those few and named.
- **Named constants, not magic numbers.** Screen bounds, speeds, colors, sprite ids,
  and score values all get names at the top of the file.
- **Data-driven over hardcoded.** Enemy rows, wave timings, and point values belong in
  tables you can tune, not scattered through logic.
- **Pure update functions where practical.** `update_x(entity, dt)` mutating one entity
  is fine; a function that touches four unrelated globals is not.
- **Comment the non-obvious only.** Explain *why* a magic timing value was chosen or
  why a formula is shaped oddly. Do not narrate what the code plainly says.
- **No dead code, no commented-out blocks, no speculative abstraction.** Delete it;
  it is recoverable from history.
- Indent with 2 spaces. Keep lines under 100 characters.

---

## 6. Definition of done, per milestone

A milestone is complete when all of the following hold:

- [ ] `game.lua` loads in TIC-80 with no console errors.
- [ ] The milestone's acceptance criteria in `MISSION.md` are observably met.
- [ ] Every new TIC-80 API call used is recorded in `docs/tic80-api.md`.
- [ ] No debug `trace()` calls fire during normal play.
- [ ] Frame rate holds at 60 with the milestone's worst-case entity count on screen.
- [ ] `PROGRESS.md` updated: what shipped, what was decided, what is still open.

---

## 7. Scope discipline

Build what `MISSION.md` specifies. Do not add menus, shaders, particle systems,
alternate game modes, or engine abstractions that the spec does not call for.

If you believe the spec is wrong, say so in one or two sentences, then implement it
as written and note the concern in `PROGRESS.md`. Scope changes are the user's call.
