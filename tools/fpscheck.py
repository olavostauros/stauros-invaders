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

The milestone's worst case has to be on screen while it measures, so --hold writes a
gamepad mask to RAM every frame, the same way tools/inputsim.py does. Both samples hold
the same mask, so the per-frame load is identical and the differential stays valid.

--hold only reaches a worst case made of things a button controls. An entity that
arrives on a timer - the saucer, which comes 15 to 25 seconds in - can miss both samples
entirely, so --samples moves the window to where it is on screen. Say in the report which
window was measured and whether the saucer was up for it.

Usage:
    python3 tools/fpscheck.py
    python3 tools/fpscheck.py --hold 24   # right + fire held throughout
    python3 tools/fpscheck.py --hold 24 --samples 1200 2400   # with the saucer up
"""

import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHORT, LONG = 300, 1200


def samples():
    """The two sample lengths, so a differential can be taken over a window that contains
    whatever is being measured."""
    if "--samples" not in sys.argv:
        return SHORT, LONG
    i = sys.argv.index("--samples")
    return int(sys.argv[i + 1]), int(sys.argv[i + 2])


def run(sample, hold):
    probe = open(os.path.join(ROOT, "tools", "fps-probe.lua"), encoding="utf-8").read()
    probe = re.sub(r"local PROBE_SAMPLE = \d+", f"local PROBE_SAMPLE = {sample}", probe)
    probe = re.sub(r"local PROBE_HOLD = \d+", f"local PROBE_HOLD = {hold}", probe)
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
    hold = int(sys.argv[sys.argv.index("--hold") + 1]) if "--hold" in sys.argv else 0
    short, long = samples()
    line_s, host_s = run(short, hold)
    line_l, host_l = run(long, hold)

    print(f"gamepad mask {hold} held throughout")
    print(f"sample {short:5d}: console {line_s}   host {host_s:.2f} s to the trace")
    print(f"sample {long:5d}: console {line_l}   host {host_l:.2f} s to the trace")

    frames, secs = long - short, host_l - host_s
    print(f"\ndifferential: {frames} extra frames in {secs:.2f} extra wall-clock "
          f"seconds -> {frames / secs:.2f} FPS")


if __name__ == "__main__":
    main()
