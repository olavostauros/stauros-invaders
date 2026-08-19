# TIC-80 RAM map — regions actually used

Per `AGENTS.md` §4.4 this records only the addresses this project touches, not the whole
96 KB map. Read 2026-08-16 from https://github.com/nesbox/TIC-80/wiki/RAM

Console version in use: **1.1.2837 (be42d6f)**.

---

## SCREEN / VRAM — byte `0x00000`

The video bank starts at byte address 0. The screen is **240 × 136 = 32,640 pixels at
4 bits each**, so 16,320 bytes, stored two pixels per byte: **low nibble is the left
pixel, high nibble is the right pixel**.

Because `peek4` addresses by nibble in that same order (`docs/tic80-api.md`), the packing
cancels out and a pixel's address is simply:

```lua
peek4(y * 240 + x)   -- palette index 0..15 of the pixel at (x, y)
```

This is how `tools/screendump.py` verifies visual acceptance criteria without a
screenshot tool. Confirmed 2026-08-16: dumping the M0 cart this way produced a legible
"HELLO" in color 12 against color 0, matching what `game.lua` draws.

Two notes for later milestones:

- VRAM is a **bank**. `vbank(1)` switches to a second 16 KB video bank with its own
  screen and palette; anything reading VRAM has to know which bank is selected. Nothing
  uses `vbank` yet — document it here before the first use if that changes.
- The region is 16,384 bytes but only the first 16,320 are the framebuffer. The
  remainder holds palette, palette map, border color, screen offset, and mouse cursor —
  look each up before poking it rather than assuming an offset.

## TILES — byte `0x04000`, and SPRITES — byte `0x06000`

8,192 bytes each. Tiles are sprite ids **0..255** at `0x4000 + 32 * id`; sprites are ids
**256..511** at `0x6000 + 32 * (id - 256)`. `spr()` addresses both ranges through one
0..511 index (`docs/tic80-api.md`).

Each 8 × 8 tile is 32 bytes: 4 bits per pixel, two pixels per byte, **low nibble is the
left pixel**, rows laid out top to bottom. That is the same packing as VRAM, so in
`poke4`'s nibble addressing a tile is 64 consecutive nibbles in plain row-major order:

```lua
poke4(0x8000 + 64 * id + 8 * row + col, color)   -- tile ids 0..255, row/col 0..7
```

The cart carries only a `CHUNK_CODE` chunk (`pack.py`), so it ships **no sprite sheet**.
`game.lua` writes the sheet here in `BOOT()` from a table of pixel rows. Confirmed
2026-08-16: the player sprite blitted this way drew 35 pixels of color 5 in the expected
shape, read back through `tools/screendump.py`.

The sheet is **16 tiles to a row**, which is what `spr()`'s `w`/`h` composite block is
laid out against: "left-to-right then top-to-bottom from `id`" (`docs/tic80-api.md`) means
`w = 2` draws `id` and `id + 1` side by side only while `id % 16 < 15`. An `id` of 15 with
`w = 2` takes 15 and 16, which are on different rows and 8 pixels apart vertically on the
sheet but drawn side by side on screen.

Measured 2026-08-18 rather than read, because no page states the row width outright:
tile 9 was filled with color 2 and tile 10 with color 3, then drawn with
`spr(9, 0, 0, -1, 1, 0, 0, 2, 1)`. Pixel (0, 0) came back 2, pixel (8, 0) came back 3, and
pixel (0, 8) came back 0 — the two tiles land horizontally adjacent and nothing bleeds into
the row below.

## GAMEPADS — byte `0x0FF80`

4 bytes, one per controller, one bit per button: player 1 is byte `0x0FF80`, bit `n` for
button `n` (so left is `1 << 2`, right `1 << 3`, A `1 << 4`).

`game.lua` never touches this. `tools/` writes it to simulate input, which no tool in
this environment can otherwise do. Confirmed 2026-08-16: poking the byte inside `TIC()`
makes `btn()` report the button held, on the same frame. It does **not** make `btnp()`
behave — see the `btnp` gotcha in `docs/tic80-api.md`.

## WAVEFORMS — byte `0x0FFE4`, and SFX — byte `0x100E4`

Read 2026-08-18 from https://github.com/nesbox/TIC-80/wiki/RAM, with the layout of one
sample taken from the console's own `tic_sample` struct in `src/tic.h` (the wiki's
`.tic` File Format page describes the chunk but is ambiguous about how a tick is packed).

The cart ships no SFX chunk, so both regions boot zeroed and `game.lua` writes them in
`BOOT()` — the same arrangement as the sprite sheet above.

**WAVEFORMS** is 256 bytes: 16 waveforms of 32 four-bit points each, so waveform `w`
starts at nibble `0x0FFE4 * 2 + w * 32` and each point is one `poke4`.

A waveform whose 32 points are **all 0 or all 15** is not a flat tone — the console reads
it as **noise** (`tic_tool_noise()`: every byte equal, and equal to `0x00` or `0xFF`).
That is where both of the game's explosions get their hiss, and it is also why an
unwritten waveform is not silence.

**SFX** is 4,224 bytes: 64 samples of 66 bytes. Sample `s` starts at byte
`0x100E4 + s * 66`, and every field of it is a nibble, so the whole sample is 132
consecutive `poke4`s:

| Nibble | Holds |
|---|---|
| `4t + 0` | volume of tick `t`, **stored as 15 minus the level it plays at** |
| `4t + 1` | waveform index of tick `t` |
| `4t + 2` | chord of tick `t` — semitones added to the note the `sfx()` call names |
| `4t + 3` | pitch of tick `t` — a raw frequency offset, signed; unused here |
| `120` | octave (bits 0..2) and the 16x pitch flag (bit 3) |
| `121` | speed (bits 0..2, signed) and **reverse** (bit 3), which subtracts the chord |
| `122` | note (bits 0..3) and the two stereo mute flags |
| `123..131` | loop start and size for each of wave, volume, chord and pitch |

There are 30 ticks, so nibbles 0..119 are the envelope. `game.lua` supplies the note, the
octave and the speed through the `sfx()` call and writes zeros over the rest, so the only
settings nibble it ever sets is reverse.

Confirmed in-console 2026-08-18 (`scratch/sfxtest.lua`, `scratch/sfxtest2.lua`): a sample
written this way played back at the note asked for, a chord of two semitones a tick with
reverse set walked the frequency down 262, 233, 208, 185, 165, 147, 131, 117 Hz, and a
waveform of 32 zeros came back in the register as 32 zeros.

## SOUND REGISTERS — byte `0x0FF9C`

72 bytes: four channels of 18. Channel `c` starts at byte `0x0FF9C + c * 18`:

| Byte | Holds |
|---|---|
| 0 | frequency, low 8 bits |
| 1 | frequency high 4 bits in the **low** nibble, volume 0..15 in the **high** nibble |
| 2..17 | the 32-point waveform the sample copied in |

The console rewrites all four every frame from whatever the channels are playing, and
zeroes them first — so **volume 0 means the channel is silent**, and a nonzero volume is
the only evidence available here that a sound is actually coming out. `tools/input-probe.lua`
reads frequency and volume per channel and traces them; `LINT-RULES.md` L065 is the rule
that every audio claim goes through them.

Frequencies are the console's own note table, which a cart cannot read. The eight notes
`game.lua` names were measured off these registers (`scratch/notes.lua`, 2026-08-18):
note 30 → 92 Hz, 32 → 104, 34 → 117, 36 → 131, 48 → 262, 50 → 294, 55 → 392, 60 → 523.

## Not yet used

`PERSISTENT MEMORY` at `0x14004` (1,024 bytes) backs `pmem`, which M7 uses through the API
rather than by poking; its slot semantics are in `docs/tic80-api.md`. `MUSIC PATTERNS` at
`0x11164` and `MUSIC TRACKS` at `0x13E64` back `music()`, which nothing calls: the fleet's
four-note loop is one `sfx()` per march step, not a tracker pattern.
