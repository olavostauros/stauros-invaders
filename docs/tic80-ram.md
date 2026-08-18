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

## Not yet used

`PERSISTENT MEMORY` at `0x14004` (1,024 bytes) backs `pmem` and arrives in M7. Record its
details here when the high score gets written, not before.
