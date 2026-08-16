# TIC-80 API — verified signatures

Per `AGENTS.md` §4.1, every TIC-80 function used in `game.lua` is recorded here before
its first use. Each entry carries the source URL and the date it was read.

Console version in use: **1.1.2837 (be42d6f)**.

Optional parameters are shown in brackets with their defaults. TIC-80 uses positional
optionals — a skipped middle argument shifts everything after it, so pass explicitly.

---

## Callbacks

### `TIC()`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/TIC

```lua
function TIC() end
```

No parameters, no return value. Called sixty times per second. Mandatory in every
cartridge — all update and draw work happens inside it.

### `BOOT()`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/BOOT

```lua
function BOOT() end
```

No parameters, no return value. Called once when the cartridge boots, before the first
`TIC()`. Added in API version 1.00. Preferred over global-scope initialization.

---

## Drawing

### `cls`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/cls

```lua
cls([color=0])
```

- `color` — palette index 0..15. Defaults to 0.

Returns nothing. Fills the entire screen. Not mandatory per frame; skipping it stacks
frames, which is a deliberate effect rather than a bug.

### `print`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/print

```lua
print(text, [x=0], [y=0], [color=15], [fixed=false], [scale=1], [smallfont=false])
-> width
```

- `text` — string to draw.
- `x`, `y` — top-left position. Default 0, 0.
- `color` — palette index. Default 15.
- `fixed` — fixed-width font. Default false.
- `scale` — integer font scale. Default 1.
- `smallfont` — use the small font. Default false.

**Returns the rendered width in pixels.** Use that return to center text rather than
hardcoding an offset.

**Gotcha:** the default `color=15` is dark navy (`#333C57`) in SWEETIE-16, which is
near-invisible against the default black `cls()`. Always pass a color explicitly.

---

## Memory

### `peek4`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/peek
(the `peek4` page now redirects there)

```lua
peek4(addr4) -> val4
```

- `addr4` — **nibble** address, not a byte address. Returns 0..15.

The scaling is the trap: nibble address = byte address × 2, least-significant nibble
first. The wiki's own example is that byte `0x4000` is nibbles `0x8000` (low) and
`0x8001` (high). `peek`, `peek2`, and `peek1` are the same idea at 8-, 2-, and 1-bit
granularity, each with its own address scale.

Used by `tools/screendump.py` to read the framebuffer; see `docs/tic80-ram.md`.

---

## System

### `exit`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/exit

```lua
exit()
```

No parameters, no return value. Returns to the TIC-80 console.

**Two gotchas.** It does not return immediately — execution stops only *after* the
current `TIC()` finishes, so every line after the `exit()` call still runs. And it
returns to the console rather than quitting the process, so a script driving `tic80`
must kill it; waiting for the process to end will hang.

### `time`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/time

```lua
time() -> ms
```

No parameters. Returns milliseconds elapsed since the cartridge began execution — the
zero point is cart start, not console start.

Measured against the host wall clock 2026-08-16 via `tools/fpscheck.py`: 900 frames of
`time()` and 15.00 s of host time agree to within 0.02 FPS, so it tracks real time and
is not derived from the frame counter.

### `trace`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/trace

```lua
trace(message, [color=15])
```

- `message` — string or simple variable; non-strings are converted automatically.
- `color` — palette index for the console line. Default 15.

Returns nothing. Prints to the TIC-80 console, not to the screen. Concatenate with
`..` to combine values.

---

## Palette

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/Palette

Default palette is SWEETIE-16:

| Index | Hex | Name | Index | Hex | Name |
|---|---|---|---|---|---|
| 0 | 1A1C2C | black | 8 | 29366F | dark blue |
| 1 | 5D275D | purple | 9 | 3B5DC9 | blue |
| 2 | B13E53 | red | 10 | 41A6F6 | light blue |
| 3 | EF7D57 | orange | 11 | 73EFF7 | cyan |
| 4 | FFCD75 | yellow | 12 | F4F4F4 | white |
| 5 | A7F070 | light green | 13 | 94B0C2 | light grey |
| 6 | 38B764 | green | 14 | 566C86 | grey |
| 7 | 257179 | dark green | 15 | 333C57 | dark grey |

---

## Cartridge metadata

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/Cartridge-Metadata

Tags go at the very top of the source as `--` comments, one per line.

| Tag | Purpose | Notes |
|---|---|---|
| `title` | Game name | Required for tic80.com upload |
| `author` | Developer name | Required for tic80.com upload |
| `desc` | Description | Optional |
| `script` | Language | `lua` is the default; state it anyway |
| `input` | `gamepad`, `keyboard`, or `mouse` | Only affects on-screen Android controls; does not restrict `btn`/`key` |
| `saveid` | Persistent-memory identifier | Highly recommended when using `pmem` — it keys the save slot |
| `menu` | Space-separated menu items | Optional |
