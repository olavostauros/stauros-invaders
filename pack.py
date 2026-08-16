#!/usr/bin/env python3
"""Pack game.lua into a minimal binary game.tic.

The installed TIC-80 is not PRO, and non-PRO builds refuse text cartridges:
"This version only supports binary .png or .tic cartridges." This produces the
smallest cart the console will accept - a single CHUNK_CODE chunk holding the
source verbatim.

game.lua remains the source of truth. game.tic is generated and gitignored.

Format: https://github.com/nesbox/TIC-80/wiki/.tic-File-Format (read 2026-08-16)
  byte 0     bank << 5 | chunk type
  bytes 1-2  chunk size, little-endian, 16-bit
  byte 3     reserved
  byte 4+    chunk data
"""

import sys

CHUNK_CODE = 5
BANK = 0
# The size field is 16-bit, so one bank tops out here. AGENTS.md 2 says report
# rather than silently minify if the cart approaches its cap.
MAX_CODE = 0xFFFF

def pack(src="game.lua", dst="game.tic"):
    with open(src, "rb") as f:
        code = f.read()

    if len(code) > MAX_CODE:
        sys.exit(
            f"{src} is {len(code)} bytes, over the {MAX_CODE}-byte single-bank limit.\n"
            "Splitting across banks or compressing is a real decision - make it "
            "deliberately, do not minify silently."
        )

    header = bytes([
        BANK << 5 | CHUNK_CODE,
        len(code) & 0xFF,
        (len(code) >> 8) & 0xFF,
        0,
    ])

    with open(dst, "wb") as f:
        f.write(header + code)

    pct = 100 * len(code) / MAX_CODE
    print(f"{dst}: {len(code)} bytes of code ({pct:.1f}% of one bank)")

if __name__ == "__main__":
    pack(*sys.argv[1:])
