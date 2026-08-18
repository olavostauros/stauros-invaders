# Lua notes — TIC-80's embedded interpreter

TIC-80-specific Lua facts confirmed against the running console, per `AGENTS.md` §4.4.

## Version

**Lua 5.3.** Confirmed 2026-08-16 by `trace(_VERSION)` in `BOOT()`, run headless on
TIC-80 1.1.2837 (be42d6f):

```
$ tic80 --fs=. --cli --skip --cmd="load game.tic & run"
cart game.tic loaded!
use RUN command to run it
Lua 5.3
```

This resolves the open question in `PROGRESS.md` §6. It is **not** the host-side
`lua5.4` in `/usr/bin` — the console is a full minor version behind.

### What 5.3 gives us

Available, per https://www.lua.org/manual/5.3/ (read 2026-08-16):

- Integer division `//` and integer/float subtypes, `math.type`, `math.tointeger`
- Bitwise operators `& | ~ << >>`
- `goto` and labels
- `string.pack` / `string.unpack`

### What it does not

5.4-only, and a syntax error in the console even though host `luac5.4` accepts them:

- `<close>` and `<const>` variable attributes
- `warn()`, `coroutine.close`
- The generational GC interface

Gone since 5.2 and earlier, so do not reach for them from memory:

- `unpack` → use `table.unpack`
- `loadstring` → use `load`
- `bit32` → use the native operators above
- `math.atan2` → use `math.atan(y, x)`
- `math.pow`, `math.ldexp`, `math.frexp` → use `^` and arithmetic

### Consequence for syntax checking

`luac5.4 -p game.lua` is checking against the **wrong interpreter version** — it is a
superset, so it will happily accept 5.4-only syntax that the console rejects at load.
It catches ordinary typos, which is most of its value, but it is not authoritative.
`lua5.3` is available in the Ubuntu archive (`5.3.6-3`) and not currently installed;
installing it would make the check match the target. Tracked as `LINT-RULES.md` L005.

## Standard library availability

Confirmed present: `math` (via `math.floor`), `_VERSION`, `ipairs`, `tostring`, and the
`string` and `table` tables — `string.format`, `string.sub` including the `s:sub()`
method form, and `table.concat` all run in-console (2026-08-16, `game.lua` and
`tools/`).

### `math.random` is present, and the console seeds it from the clock

Confirmed 2026-08-17 for M4's enemy fire. `math.random` exists in both forms —
`math.random(m)` for an integer in `1..m` and `math.random()` for a float in `[0,1)`.

The **two-argument form `math.random(m, n)`**, an integer in `m..n`, is also present.
Confirmed 2026-08-18 for M6's saucer interval: `math.random(900, 1500)` returned 1142 and
1087 in one run. Recorded separately because the note above listed only the other two forms
and its silence read as an absence.

**The stream is not reproducible across runs, and a cart must not be written as if it
were.** Six headless runs of the same cart, spaced three seconds apart, returned six
different sequences (`3 5 9 4 1`, `6 9 3 7 8`, `8 8 2 5 4`, `11 2 7 3 6`, `8 11 1 1 2`,
`11 11 7 4 4` from `math.random(11)`). TIC-80 1.1.2837 seeds the generator itself; the
cart never calls `math.randomseed`.

**DISCREPANCY, resolved:** an earlier note here claimed the opposite — that three
consecutive runs came back byte for byte identical — and that measurement was real but
misread. The seed has roughly one-second granularity: four runs launched *simultaneously*
returned `3 11 4 6 4` four times over, and two launched two seconds later agreed with each
other and differed from those. Runs fast enough to land in the same second share a stream,
which is exactly what a back-to-back check produces. `AGENTS.md` §4.3 is the rule this
broke: the conclusion outran the experiment.

The consequence is for `tools/`, not for `game.lua`: a scenario may not depend on which
column fires or on which frame the ship dies, and cannot re-run a script expecting the
same shots. Assert the *rule* — grid alignment, cadence, bottom-most-in-column — over
whatever the fleet happens to do that run.

Everything else is **unverified**. `AGENTS.md` §2 says to assume `require`, `io.*`,
`os.execute`, file access, and `package` are unavailable until proven otherwise, and
nothing so far has proven otherwise. Test in-console before using any stdlib table not
listed as confirmed here, and add the result to this section.
