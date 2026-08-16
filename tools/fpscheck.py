#!/usr/bin/env python3
"""Measure game.lua's frame rate against two independent clocks.

MISSION.md's acceptance criteria include "60 FPS", and the console's own time() is not
enough to establish it: if TIC-80 derived time() from the frame counter, "60 FPS over
600 frames" would be true by construction. So this also times the run from outside.

The host side needs care. tic80 does not terminate when the cart calls exit() - it
drops back to its console and sits there - and process startup plus stdout buffering
add an unknown constant. Both cancel in a differential: run the same probe at two
sample lengths and divide the extra frames by the extra wall-clock seconds.

Runs windowed on purpose. --cli is unthrottled, with no vsync and no frame limiter, so
it measures the host CPU rather than the console's pacing.

Usage:
    python3 tools/fpscheck.py
"""

import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORT, LONG = 300, 1200


def run(sample):
    probe = open(os.path.join(ROOT, "tools", "fps-probe.lua"), encoding="utf-8").read()
    probe = re.sub(r"local PROBE_SAMPLE = \d+", f"local PROBE_SAMPLE = {sample}", probe)
    os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
    with open(os.path.join(ROOT, "scratch", "fps.lua"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "game.lua"), encoding="utf-8").read() + probe)
    subprocess.run([sys.executable, "pack.py", "scratch/fps.lua", "scratch/fps.tic"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

    t0 = time.monotonic()
    proc = subprocess.Popen(
        ["tic80", "--fs=.", "--skip", "--cmd=load scratch/fps.tic & run"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    buf = b""
    elapsed = None
    try:
        while time.monotonic() - t0 < 120:
            chunk = proc.stdout.read(1)
            if not chunk:
                break
            buf += chunk
            if b"FPS " in buf and buf.endswith(b"ms"):
                elapsed = time.monotonic() - t0
                break
    finally:
        proc.kill()
        proc.wait()

    text = buf.decode(errors="replace")
    if elapsed is None:
        sys.exit(f"no FPS line for sample={sample}; console output:\n{text[-2000:]}")
    return re.search(r"FPS [\d.]+ over \d+ frames in [\d.]+ ms", text).group(0), elapsed


def main():
    line_s, host_s = run(SHORT)
    line_l, host_l = run(LONG)

    print(f"sample {SHORT:5d}: console {line_s}   host {host_s:.2f} s to the trace")
    print(f"sample {LONG:5d}: console {line_l}   host {host_l:.2f} s to the trace")

    frames, secs = LONG - SHORT, host_l - host_s
    print(f"\ndifferential: {frames} extra frames in {secs:.2f} extra wall-clock "
          f"seconds -> {frames / secs:.2f} FPS")


if __name__ == "__main__":
    main()
