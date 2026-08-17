#!/usr/bin/env python3
"""Show what game.lua actually draws, without a screenshot tool.

Milestone acceptance in MISSION.md is visual, and this environment has no way to
photograph the window: grim needs a wlroots compositor and WSLg is not one, and no X11
capture tool is installed (installing one needs a sudo password, so an agent cannot).

So the pixels are read from inside the console instead. tools/vram-probe.lua is
appended to game.lua, wrapping the cart's own TIC() - the code under test runs
unmodified - and dumps the framebuffer through peek4() after the second frame. VRAM
starts at byte 0 and the screen is 240x136 4-bit pixels, so pixel (x, y) is nibble
y * 240 + x (docs/tic80-ram.md).

A frame can be dumped mid-action rather than at rest: --hold writes a gamepad mask to
RAM every frame (see tools/inputsim.py for what that does and does not simulate), and
--frames picks how many frames run before the dump. --state waits for a game state on top
of that, for screens that no frame number can be counted to - the console seeds
math.random from the clock, so the ship dies on a different frame every run.

Usage:
    python3 tools/screendump.py                       # render the occupied region
    python3 tools/screendump.py --raw out             # also write the nibble grid
    python3 tools/screendump.py --hold 16 --frames 20 # dump frame 20 with A held
    python3 tools/screendump.py --state PLAYER_DEAD   # dump the first frame of a death
"""

import os
import re
import subprocess
import sys
import time
from collections import Counter

W, H = 240, 136
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def word(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def capture(hold, frames, state):
    """Run the probe cart headlessly and return the raw console output."""
    os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
    probe = open(os.path.join(ROOT, "tools", "vram-probe.lua"), encoding="utf-8").read()
    probe = re.sub(r"local PROBE_HOLD = \d+", f"local PROBE_HOLD = {hold}", probe)
    probe = re.sub(r"local PROBE_WARMUP = \d+", f"local PROBE_WARMUP = {frames}", probe)
    probe = re.sub(r'local PROBE_STATE = ""', f'local PROBE_STATE = "{state}"', probe)
    src = os.path.join(ROOT, "scratch", "probe.lua")
    with open(src, "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "game.lua"), encoding="utf-8").read())
        f.write(probe)
    subprocess.run([sys.executable, "pack.py", "scratch/probe.lua", "scratch/probe.tic"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

    # exit() returns to the TIC-80 console rather than quitting the process, so read
    # until the dump is complete and then kill it.
    proc = subprocess.Popen(
        ["tic80", "--fs=.", "--cli", "--skip", "--cmd=load scratch/probe.tic & run"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    buf = b""
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < 60:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            if b"VRAMEND" in buf:
                break
    finally:
        proc.kill()
        proc.wait()
    return buf.decode(errors="replace")


def parse(blob):
    """Extract the nibble grid. --cli prints trace() output with no line break between
    calls, so the dump arrives as one flat stream rather than 136 lines."""
    if "VRAMBEGIN" not in blob or "VRAMEND" not in blob:
        sys.exit("the cart did not reach the probe. console output:\n" + blob[-2000:])
    body = "".join(blob.split("VRAMBEGIN", 1)[1].split("VRAMEND", 1)[0].split())
    if len(body) != W * H:
        sys.exit(f"expected {W * H} pixels between the markers, got {len(body)}")
    return [body[y * W:(y + 1) * W] for y in range(H)]


def report(rows):
    hist = Counter(c for r in rows for c in r)
    print("palette histogram (. is index 0):")
    for c, n in sorted(hist.items(), key=lambda kv: -kv[1]):
        print(f"  {c}: {n:6d} px ({100 * n / (W * H):5.2f}%)")

    lit = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c != "."]
    if not lit:
        print("\nscreen is entirely color 0 - nothing was drawn")
        return

    x0, x1 = min(p[0] for p in lit), max(p[0] for p in lit)
    y0, y1 = min(p[1] for p in lit), max(p[1] for p in lit)
    print(f"\nnon-black bounding box: x {x0}..{x1} ({x1 - x0 + 1} px), "
          f"y {y0}..{y1} ({y1 - y0 + 1} px)")
    print(f"margins: left {x0}, right {W - 1 - x1}, top {y0}, bottom {H - 1 - y1}")

    pad = 2
    print("\noccupied region, one char per pixel:")
    for y in range(max(0, y0 - pad), min(H, y1 + pad + 1)):
        seg = rows[y][max(0, x0 - pad):min(W, x1 + pad + 1)]
        print(f"{y:3d} |" + "".join(" " if c == "." else "#" for c in seg))


def main():
    hold, frames, state = arg("--hold", 0), arg("--frames", 2), word("--state", "")
    print(f"gamepad mask {hold} held, dumping frame {frames}"
          + (f" or the first one in {state} after it" if state else "") + "\n")
    rows = parse(capture(hold, frames, state))
    if "--raw" in sys.argv:
        path = sys.argv[sys.argv.index("--raw") + 1]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
        print(f"raw nibble grid written to {path}\n")
    report(rows)


if __name__ == "__main__":
    main()
