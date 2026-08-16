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

## Not yet used

`PERSISTENT MEMORY` at `0x14004` (1,024 bytes) backs `pmem` and arrives in M7. Record its
details here when the high score gets written, not before.
