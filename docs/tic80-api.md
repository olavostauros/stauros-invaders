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

Measured in-console 2026-08-18 (`scratch/font.lua`, `scratch/font2.lua`, read back through
`peek4`): the default font draws every glyph in a **6 px wide cell, 6 rows tall**, and
`fixed = true` makes that width uniform — `"SCORE 00000"` is 66 px fixed against 64 px
proportional, `"W"` is 6 px and `"i"` is 3 px proportional, and descenders in `gjp` stay
inside the six rows. The small font is 4 px wide. Because the fixed cell is exactly 6 px,
`game.lua` centres by arithmetic (`#text * FONT_W * scale`) rather than by drawing once off
screen to read the width back; fixed width is also what stops the score jittering as its
digits change.

**Gotcha:** the default `color=15` is dark navy (`#333C57`) in SWEETIE-16, which is
near-invisible against the default black `cls()`. Always pass a color explicitly.

### `spr`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/spr

```lua
spr(id, x, y, [colorkey=-1], [scale=1], [flip=0], [rotate=0], [w=1], [h=1])
```

- `id` — sprite index 0..511. 0..255 are the tiles at RAM `0x4000`, 256..511 the
  sprites at `0x6000` (`docs/tic80-ram.md`).
- `x`, `y` — top-left corner on screen.
- `colorkey` — palette index drawn as transparent. Default `-1`, meaning fully opaque,
  so a sprite drawn without one paints its background over whatever is behind it.
- `scale` — integer scale factor. Default 1.
- `flip` — 0 none, 1 horizontal, 2 vertical, 3 both. Default 0.
- `rotate` — 90° steps. Default 0.
- `w`, `h` — draw a composite block of `w × h` sprites, consumed left-to-right then
  top-to-bottom from `id`. Default 1, 1.

Returns nothing.

### `rect`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/rect

```lua
rect(x, y, width, height, color)
```

- `x`, `y` — top-left corner. `width`, `height` — size in pixels.
- `color` — palette index for the fill.

No optional parameters and no return value. Filled; `rectb` draws only the border.

---

## Input

### `btn`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/btn

```lua
btn(id) -> is_pressed
btn()   -> gamepads bitfield
```

- `id` — button 0..31. Returns whether it is **held this frame**.
- Called with no argument, returns all 32 button states as one integer.

Indices below 0 or above 31 wrap rather than erroring.

### `btnp`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/btnp

```lua
btnp(id, [hold], [period]) -> is_pressed
btnp()                     -> gamepads bitfield
```

- `id` — button 0..31. Returns true only on the frame the button **became** pressed.
- `hold` — ticks a held button waits before auto-repeat begins.
- `period` — ticks between repeats once `hold` has elapsed.

**Gotcha, and the one place this project deliberately omits optional arguments
(`LINT-RULES.md` L007):** `hold` and `period` are what *turn on* auto-repeat. Omitting
both is the only documented way to get exactly one true per press, which is what the
single-bullet rule needs. Supplying them makes a held button fire repeatedly.

**DISCREPANCY (not with the docs, but with RAM):** `btnp` compares against a snapshot of
the previous frame's input taken from the real input device, *not* from the GAMEPADS
region of RAM. Writing that region with `poke` therefore drives `btn` correctly but makes
`btnp` return true on every frame of a simulated hold — measured 2026-08-16, true on all
nine frames of a poked hold. This is why `tools/inputsim.py` substitutes its own `btnp`,
and it keeps a standing scenario watching for the day the console's behavior changes.

### Button ids

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/key-map

Player 1 is 0..7; each further player adds 8, so player 2 is 8..15 and so on.

| Id | Button | Id | Button |
|---|---|---|---|
| 0 | up | 4 | A |
| 1 | down | 5 | B |
| 2 | left | 6 | X |
| 3 | right | 7 | Y |

Confirms `MISSION.md` §7's left/right/A as 2/3/4.

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

### `poke`, `poke4`

Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/poke

```lua
poke(addr, val, [bits=8])
poke4(addr4, val4)
```

- `poke(addr, val)` writes one byte, `val` 0..255, at byte address `addr`.
- `poke4(addr4, val4)` writes one nibble, `val4` 0..15, at **nibble** address
  `addr4` — twice the byte address, low nibble first. `poke4(a, v)` and
  `poke(a, v, 4)` are the same call.
- `poke2` and `poke1` follow at 2- and 1-bit granularity, each with its own scale.

Returns nothing. `game.lua` uses `poke4` to blit its sprite sheet into tile RAM at boot;
`tools/` uses `poke` to write the gamepad byte.

### `pmem`

Read 2026-08-18 from https://github.com/nesbox/TIC-80/wiki/pmem

```lua
pmem(index)        -> val32   -- read
pmem(index, val32) -> val32   -- write, returning the value that was there before
```

- `index` — slot, integer 0..255. There are 256 slots.
- `val32` — 32-bit **unsigned** integer, 0..4294967295. Omitting it makes the call a read.

**Returns the prior value on a write**, not the value written. A slot never written reads
as 0.

**Gotcha, and the reason the cartridge header matters:** saved data is keyed on an MD5
hash of the script by default, so *editing the cart erases the save*. Declaring
`-- saveid:` in the metadata header overrides that and keys the data on the string
instead. `game.lua` carries `-- saveid: STAUROSINVADERS`, which is what lets a high score
outlive an edit.

Verified in-console 2026-08-18 by `scenario_high_score` in `tools/inputsim.py`: a slot
written to 0 before boot reads back as 0, a game that scored 10 and ended wrote 10, and a
second console launched afterwards read 10 out of the slot on its first frame.

---

## Audio

### `sfx`

Read 2026-08-18 from https://github.com/nesbox/TIC-80/wiki/sfx

```lua
sfx(id, [note=-1], [duration=-1], [channel=0], [volume=15], [speed=0])
```

- `id` — sound effect 0..63, or **-1 to stop the channel**.
- `note` — either a number 0..95, or a string like `"C#4"`. As a number it is
  `12 * octave + semitone`, so 48 is C-4 and 60 is C-5. -1 keeps the sample's own note.
- `duration` — frames; -1 plays until the sample runs out of envelope.
- `channel` — 0..3. Four sounds can play at once, one per channel; a second `sfx()` on a
  channel replaces what was there.
- `volume` — 0..15, applied on top of the sample's own per-tick envelope.
- `speed` — -4..3. It stretches or compresses the sample: at 0 one tick lasts one frame,
  at -1 two frames, and above 0 it skips ticks instead. Anything outside the 3-bit signed
  range — the default, 8 — means "use the sample's own speed".

Returns nothing. `game.lua` calls it with all six arguments always (L007), which is also
what makes the stop call read oddly: `sfx(-1, -1, -1, channel, 15, 0)`, because the
channel cannot be named without the note and duration in front of it.

**Where the sound itself comes from:** `sfx()` plays sample `id` out of the cartridge's
SFX bank. This cart has no SFX chunk (`pack.py` writes code and nothing else), so the bank
boots empty and `game.lua` writes it into RAM at boot, the same way it writes its sprite
sheet — see `docs/tic80-ram.md` for the layout of a sample.

Verified in-console 2026-08-18 by `scratch/sfxtest.lua` and by five scenarios in
`tools/inputsim.py`: a sample poked into the bank and played with `sfx(0, 60, 10, 0, 15, 0)`
put 523 Hz on channel 0 with the volume falling 15, 14, 13 … one step a frame, and the
channel fell silent when the envelope ran out. Two behaviours worth having written down,
both measured rather than read:

- **The register catches up a frame later.** A sound called for on frame *n* first appears
  in the sound registers on frame *n + 1*. Every audio assertion in `tools/inputsim.py`
  is offset by it (L065).
- **A tick whose stored volume is 15 silences the channel.** The bank stores `15 - level`,
  so an envelope shorter than 30 ticks ends the sound by itself, whatever `duration` says.

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
