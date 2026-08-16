# LINT-RULES.md

Lint rules for `game.lua`. Run the full pass before closing any milestone
(`AGENTS.md` §6).

There is no linter binary in this environment — no `luacheck`, no `selene`. These rules
are enforced with `luac5.4`, `grep`, and `awk`, plus a short list of checks that only a
reading agent can do. Rules that can be automated are; the rest say so plainly.

Every rule states what it forbids and *why it exists*, because a rule whose reason is
forgotten gets argued away later. Rules trace back to `AGENTS.md`; where they do, the
section is cited.

---

## Running the pass

From the repo root:

```bash
luac5.4 -p game.lua                             # L001
luac5.4 -l -p game.lua | grep -oE '_ENV "[A-Za-z_][A-Za-z0-9_]*"' | sort -u   # L010, L011
awk 'length > 100 {print FILENAME":"FNR": "length" chars"}' game.lua          # L020
grep -nP '\t| +$' game.lua                                                    # L021
grep -nE '^\s*--.*(===|---|\*\*\*|###|___|[─│┌┐└┘█▀▄])' game.lua              # L030
grep -nE -e '--.*\b(TODO|FIXME|XXX|HACK|NOTE)\b' game.lua                     # L031
grep -nE '\b(require|dofile|loadfile|io\.|os\.|package\.|collectgarbage)' game.lua  # L002
grep -nE 'while +true|repeat' game.lua                                        # L003
grep -nE '(^|[^-])//|[^:]goto |<<|>>|math\.type|<close>' game.lua             # L005
grep -n 'DEBUG *= *true' game.lua                                             # L041
[ game.tic -nt game.lua ] || echo "L050: game.tic is stale, run python3 pack.py"
```

Each command should print nothing, except the `_ENV` one — that prints the global list,
which you read against L010's allowlist.

Closing a milestone additionally needs the two checks that require running the cart.
They take seconds and half a minute respectively, so they are milestone-close rather
than every-edit:

```bash
python3 tools/screendump.py    # L051 - what is actually on screen
python3 tools/fpscheck.py      # L052 - frame rate, windowed
```

---

## Correctness rules

These catch cartridges that fail to run or fail silently. Silent failure is the common
case in TIC-80: a wrong argument usually draws nothing rather than raising.

### L001 — the file must parse
`luac5.4 -p game.lua` exits clean. A syntax error is the one thing `AGENTS.md` §3 rule 3
never permits handing back. **Automated.**

*This is a parse check, not a test. It says nothing about behavior.* It also checks
against the wrong version — the console runs Lua 5.3 and the host `luac` is 5.4, a
superset. See L005.

### L002 — no host-environment library calls
No `require`, `dofile`, `loadfile`, `io.*`, `os.*`, `package.*`. TIC-80 embeds a subset
of Lua and has no filesystem (`AGENTS.md` §2). These parse fine under host `luac5.4` and
then fail inside the console, which is why the check is grep and not the parser.
**Automated.**

### L003 — no unbounded loops
No `while true`, no `repeat` without an obviously bounded condition. `TIC()` is called by
the console 60 times a second; there is no loop for you to own and no way to block
(`AGENTS.md` §2). A blocking loop freezes the console with no error. **Automated,
then read** — `repeat` is legal when its termination is plain.

### L004 — the metadata header survives every edit
The first lines of `game.lua` are the `--`-prefixed metadata block including
`-- script: lua` and `-- saveid:`. Without `script` the console may pick the wrong
interpreter; changing `saveid` orphans every `pmem` slot saved under the old one
(`AGENTS.md` §2, `docs/tic80-api.md`). **Read.**

### L005 — no Lua syntax newer than the console's Lua 5.3
The console embeds **Lua 5.3**, confirmed 2026-08-16 (`docs/lua-notes.md`). So `//`,
`goto`, and the bitwise operators are fine; `<close>`, `<const>`, `warn()`, and
`coroutine.close` are 5.4-only and will fail at load. Also gone: `unpack`,
`loadstring`, `bit32`, `math.atan2`, `math.pow`.

The trap is that the host checker is `luac5.4`, a **superset** — it accepts every one of
those 5.4-only forms silently, so L001 will not catch them. Until `lua5.3` is installed
(`5.3.6-3` is in the archive), this rule is the only thing standing between a 5.4-ism
and a cart that will not load. **Automated, weakly** — the grep is approximate and
`//` inside a comment or URL false-positives, so read each hit.

*Updated 2026-08-16: was "until `_VERSION` is confirmed"; it now is. Installing `lua5.3`
would automate this properly and retire the grep.*

### L006 — every TIC-80 call is documented before it is used
Any function in the `_ENV` list from L011 that is a TIC-80 API call must already have a
signature entry in `docs/tic80-api.md`, with source URL and date. `AGENTS.md` §4.1, no
exceptions, including functions that feel obvious. **Read, driven by L011's output.**

### L007 — optional arguments are passed explicitly
TIC-80 signatures use positional optionals, so a skipped middle argument shifts every
argument after it. Never rely on a default you have not read in `docs/tic80-api.md`.
**Read.**

### L008 — every draw call names its color
`print`, and any later `spr`/`rect`/`line`, pass an explicit color constant. `print`
defaults to color 15, which is dark navy in SWEETIE-16 and invisible against the black
the game clears to. Nothing errors; the text simply is not there. **Read.**

### L009 — no allocation in the frame path
No table constructor (`{}`) evaluated inside `TIC()` or anything it calls per frame.
Build tables once at load or in `BOOT()`. A frame that overruns its budget drops
silently (`AGENTS.md` §2). **Read.**

---

## Structure rules

### L010 — globals are a short, deliberate allowlist
Run the `_ENV` command. Every name it prints is either a TIC-80 callback the console
calls (`TIC`, `BOOT`), a documented TIC-80 API function, a Lua stdlib table (`math`,
`table`, `string`), or one of the game's declared state tables. Anything else is an
accidental global from a missing `local` — which in TIC-80 persists across frames and
produces bugs that look like corruption. `AGENTS.md` §2, §5. **Automated + read.**

Current allowlist: `TIC`, `BOOT`, `game`, `math`, `_VERSION`, plus documented API calls.

*Amended 2026-08-16: `_VERSION` added. It is a read-only Lua stdlib global, not an
accidental one, and it appears in the `_ENV` output because `BOOT()` traces it under
`DEBUG`. Lua stdlib tables and globals belong on this list; TIC-80 calls still have to
earn their place through L006.*

### L011 — the global list is the API inventory
The same `_ENV` output is the authoritative list of which TIC-80 functions the cart
actually calls. Diff it against `docs/tic80-api.md` to enforce L006 — this is how an
undocumented call gets caught, rather than by remembering to check. **Automated.**

### L012 — named constants, not magic numbers
Screen bounds, speeds, colors, sprite ids, score values, and timing values are named
constants at the top of the file (`AGENTS.md` §5). A bare `12` in a draw call is a lint
failure even when it is correct. Loop indices and `0`/`1` identities are exempt.
**Read.**

### L013 — tunables live in tables, not in logic
Enemy rows, wave timings, and point values are data (`AGENTS.md` §5). If tuning a value
means editing a conditional, it is in the wrong place. **Read.**

### L014 — sections appear in order, labeled plainly
Metadata → constants → state → helpers → entity update → entity draw → collision →
game-state machine → `TIC()` → `BOOT()`, each introduced by one lowercase comment line
naming the section (`AGENTS.md` §5). **Read.**

### L015 — no dead code
No commented-out blocks, no unreferenced functions, no abstraction with one caller and
no second caller planned. It is all recoverable from git (`AGENTS.md` §5). **Read.**

---

## Comment rules

These implement `AGENTS.md` §5 *Comments*. They exist because generated code drifts
toward narrating itself, and narration ages into lies as the code changes underneath it.

### L030 — no decorative characters
No `=====`, `-----`, `*****`, `#####`, `_____`, box-drawing, or ASCII art in comments.
No centered or padded text, no ALL-CAPS titles. A section label is `-- constants` and
nothing more. **Automated.**

### L031 — no tracking tags
No `TODO`, `FIXME`, `XXX`, `HACK`, `NOTE`. Unfinished work goes in `PROGRESS.md` where
the next agent will actually look for it; a tag buried in source is a note to nobody.
**Automated** — the pattern needs `-e`, since a pattern starting with `--` is otherwise
parsed as a command-line flag and the check silently reports clean.

### L032 — comments explain why, never what
A comment that restates the line beneath it fails. So does a comment that would be
obvious to anyone who reads Lua. Keep the ones that justify a choice: why this timing
value, why this formula shape, why this edge case. **Read.**

### L033 — no narration and no meta-commentary
No running commentary ("now we loop over the invaders"), no step numbers, no tutorial
asides, no addressing the reader. No comment mentions a milestone, a session, a change,
or that something is done — that is `PROGRESS.md`'s job and git's job. **Read.**

---

## Debug rules

### L040 — debug output is gated
Every `trace()` sits behind the `DEBUG` flag. `AGENTS.md` §6 requires that no debug
trace fires during normal play. **Read.**

### L041 — `DEBUG` is false at milestone close
`grep -n 'DEBUG *= *true' game.lua` prints nothing when a milestone is marked `DONE`.
**Automated.**

---

## Workflow rules

### L050 — never run a stale `game.tic`
`game.tic` is newer than `game.lua` before any run you draw a conclusion from. The
console loads the binary cart, not the source, so an unpacked edit means you are
watching the previous build — and the bug you "reproduce" is one you already fixed.
**Automated:**

```bash
[ game.tic -nt game.lua ] || echo "L050: game.tic is stale, run python3 pack.py"
```

*Added 2026-08-16, when the packing step was introduced. The failure is silent by
construction, which is exactly why it needs a check rather than discipline.*

### L051 — visual acceptance is read off the framebuffer, never assumed
A milestone whose acceptance criterion in `MISSION.md` describes what is *on screen*
does not close on a clean headless run. A headless run proves the cart loaded and did
not throw; it says nothing about whether anything was drawn, in a visible color, in the
right place. `print` defaulting to an invisible color (L008) is exactly the failure that
passes a headless run and fails the criterion.

```bash
python3 tools/screendump.py       # prints the palette histogram, bounding box, and ASCII
```

**Automated, then read** — the tool renders the pixels; judging whether they match the
criterion is yours.

*Added 2026-08-16. M0 sat `IN PROGRESS` for a session because "text visible" had not
been observed and no screenshot tool works here — `grim` needs a wlroots compositor and
WSLg is not one. Reading VRAM through `peek4` from inside the console removed the
blocker entirely, and made the check cheaper than a screenshot would have been.*

### L052 — measure frame rate windowed, never under `--cli`
`AGENTS.md` §6 requires 60 FPS at the milestone's worst-case entity count. Measure it
with the console windowed:

```bash
python3 tools/fpscheck.py
```

`--cli` has no vsync and no frame limiter, so it runs as fast as the host CPU allows and
reports a number that is unrelated to the console's pacing — flattering nonsense early
on, and it would keep flattering right up until real frames started dropping.

*Added 2026-08-16, when M0's 60 FPS criterion was first actually measured. The tool
cross-checks the console's `time()` against the host wall clock, because `time()` alone
would be circular if TIC-80 derived it from the frame counter. It does not
(`docs/tic80-api.md`), and that is now a recorded fact rather than an assumption.*

### L053 — verification probes append to `game.lua`, never edit it
The harness in `tools/` concatenates a probe onto a copy of `game.lua` and wraps the
cart's own `TIC()`. Nothing in `tools/` may require an edit to `game.lua` — no probe
hooks, no instrumentation flags, no "just add a counter here". **Read.**

*Added 2026-08-16. Instrumentation that lives in the deliverable is instrumentation that
ships: it survives the milestone, drifts out of sync, and turns into the dead code L015
forbids. Wrapping the global `TIC` gets the same measurement with the code under test
running byte-for-byte as committed.*

---

## Extending these rules

**This file is expected to grow.** It is a record of mistakes worth not repeating, so
every real defect and every style slip caught in review should leave a rule behind.

When you add one:

- Give it the next unused ID in its section's range. **Never renumber and never reuse an
  ID** — rules get cited from `PROGRESS.md` and from commit messages, and a shifted
  number silently rewrites that history.
- State what it forbids, then *why*, then how it is checked. A rule without a reason
  cannot be applied to a case its author did not foresee, and gets argued away.
- Automate it if `grep`/`awk`/`luac` can, and add the command to *Running the pass*
  above. A rule that depends on an agent remembering to look is a rule that will lapse.
  Say **Read** honestly when it cannot be automated rather than writing a check that
  does not really work.
- Note the date and what triggered it. "Added 2026-08-16 after X" is what tells a later
  agent whether the rule still applies.

When a rule turns out to be wrong or obsolete, **mark it `RETIRED:` with the reason and
date; do not delete it.** Same reasoning as `PROGRESS.md` §6's answered questions — the
record of what was once believed is worth keeping, and a deleted rule invites the
mistake back.

If a rule and the running console disagree, the console wins. Fix the rule, and record
the discrepancy in `docs/tic80-api.md` per `AGENTS.md` §4.3.
