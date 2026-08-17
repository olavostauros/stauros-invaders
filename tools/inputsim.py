#!/usr/bin/env python3
"""Drive game.lua with scripted gamepad input and check what the game state does.

MISSION.md's acceptance criteria are about behavior under input ("ship moves smoothly",
"holding fire produces one bullet, not a stream"), and this environment cannot press a
key: WSLg takes input from the Windows side, and no injection tool is installed.

So the gamepad is written straight to RAM. tools/input-probe.lua is appended to
game.lua, wraps the cart's own TIC(), pokes the player-1 gamepad byte at 0x0FF80 before
each frame, and traces the game's own state afterwards. game.lua runs unmodified.

One thing the poke cannot fake: btnp compares the pad against a snapshot the console
takes from the real input device rather than from RAM, so a poked hold reads as a fresh
press on every frame (measured 2026-08-16). The probe therefore supplies its own btnp,
edge-detecting the mask it wrote - the semantics the wiki documents for a held button.
btn, the movement path, is the console's own and is exercised for real.

Usage:
    python3 tools/inputsim.py            # run every scenario, report pass/fail
    python3 tools/inputsim.py --frames   # also print the per-frame trace
"""

import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEFT, RIGHT, FIRE = 1 << 2, 1 << 3, 1 << 4
IDLE = 0

SCREEN_W, SPRITE_W = 240, 8
START_X, X_MIN, X_MAX = 116, 0, SCREEN_W - SPRITE_W
BULLET_SPEED, MUZZLE_X = 2, 3

FLEET_COLS, FLEET_COL_SPACING = 11, 16
FLEET_WIDTH = (FLEET_COLS - 1) * FLEET_COL_SPACING + SPRITE_W
FLEET_START_X, FLEET_START_Y = (SCREEN_W - FLEET_WIDTH) // 2, 20
FLEET_X_MAX = SCREEN_W - FLEET_WIDTH
FLEET_STEP_FRAMES, FLEET_STEP_X, FLEET_DROP_Y = 55, 2, 6


def run(script):
    """Run game.lua under the probe with `script` as [(frames, mask), ...] and return
    a list of per-frame dicts."""
    probe = open(os.path.join(ROOT, "tools", "input-probe.lua"), encoding="utf-8").read()
    table = "{" + ",".join(f"{{{n},{m}}}" for n, m in script) + "}"
    probe = re.sub(r"local PROBE_SCRIPT = \{\}", f"local PROBE_SCRIPT = {table}", probe)
    os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
    with open(os.path.join(ROOT, "scratch", "input.lua"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "game.lua"), encoding="utf-8").read() + probe)
    subprocess.run([sys.executable, "pack.py", "scratch/input.lua", "scratch/input.tic"],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

    # exit() drops back to the TIC-80 console instead of quitting, so read to the end
    # marker and kill the process.
    proc = subprocess.Popen(
        ["tic80", "--fs=.", "--cli", "--skip", "--cmd=load scratch/input.tic & run"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    buf = b""
    t0 = time.monotonic()
    try:
        while time.monotonic() - t0 < 120:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            if b"PROBEEND" in buf:
                break
    finally:
        proc.kill()
        proc.wait()

    text = buf.decode(errors="replace")
    if "PROBEEND" not in text:
        sys.exit("the cart did not finish the script. console output:\n" + text[-2000:])
    frames = [
        {"f": int(a), "mask": int(b), "x": int(c),
         "live": int(d), "by": int(e), "bx": int(f), "cbtnp": int(g),
         "fx": int(h), "fy": int(i), "fdir": int(j), "fframe": int(k)}
        for a, b, c, d, e, f, g, h, i, j, k in re.findall(
            r"\[(\d+) (\d+) (-?\d+) (\d) (-?\d+) (-?\d+) (\d) "
            r"(-?\d+) (-?\d+) (-?\d+) (\d)\]", text)
    ]
    total = sum(n for n, _ in script)
    if len(frames) != total:
        sys.exit(f"expected {total} frames of trace, parsed {len(frames)}")
    return frames


def shots(frames):
    """Frames on which a bullet came into existence."""
    out, prev = [], 0
    for fr in frames:
        if fr["live"] and not prev:
            out.append(fr)
        prev = fr["live"]
    return out


def check(name, ok, detail):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
    return ok


def scenario_move(mask, label, expect):
    frames = run([(300, mask)])
    xs = [fr["x"] for fr in frames]
    wrong = [(fr["f"], fr["x"], expect(fr["f"])) for fr in frames
             if fr["x"] != expect(fr["f"])]
    print(f"\nhold {label} for 300 frames")
    ok = check(f"1 px per frame then clamped at {expect(300)}",
               not wrong,
               f"x went {xs[0]} -> {xs[-1]}, every frame matched"
               if not wrong else f"{len(wrong)} mismatches, first {wrong[0]}")
    return ok


def scenario_hold_fire():
    frames = run([(300, FIRE)])
    fired = shots(frames)
    print("\nhold fire for 300 frames")
    ok = check("one bullet, not a stream", len(fired) == 1,
               f"{len(fired)} bullet(s) spawned in 300 frames of held fire")
    flight = [fr for fr in frames if fr["live"]]
    steps = {flight[i - 1]["by"] - fr["by"] for i, fr in enumerate(flight) if i}
    ok &= check(f"bullet rises {BULLET_SPEED} px per frame", steps == {BULLET_SPEED},
                f"y {flight[0]['by']} -> {flight[-1]['by']} over {len(flight)} frames, "
                f"step set {sorted(steps)}")
    ok &= check("bullet leaves the screen and frees the slot",
                flight[-1]["f"] < frames[-1]["f"],
                f"cleared on frame {flight[-1]['f'] + 1}, "
                f"idle for the remaining {frames[-1]['f'] - flight[-1]['f']} frames")
    ok &= check("bullet leaves the muzzle", fired[0]["bx"] == START_X + MUZZLE_X,
                f"bullet x {fired[0]['bx']}, ship x {fired[0]['x']}")
    return ok


def scenario_tap_fire():
    taps = 4
    frames = run([(1, FIRE), (79, IDLE)] * taps)
    fired = shots(frames)
    print(f"\ntap fire {taps} times, spaced 80 frames apart")
    return check("one bullet per press", len(fired) == taps,
                 f"{len(fired)} bullet(s) from {taps} presses, on frames "
                 f"{[fr['f'] for fr in fired]}")


def scenario_tap_while_in_flight():
    frames = run([(1, FIRE), (9, IDLE)] * 6)
    fired = shots(frames)
    print("\ntap fire 6 times, 10 frames apart, while a bullet is still in flight")
    return check("presses during flight are ignored", len(fired) == 1,
                 f"{len(fired)} bullet(s) from 6 presses")


def scenario_console_btnp():
    """Not a test of the game: a witness that the console's btnp still ignores RAM.

    If this ever fails, TIC-80 has started honouring gamepad writes and the probe's
    substitute btnp can be retired - at which point one shot per press would be verified
    against the console itself. See LINT-RULES.md L054.
    """
    frames = run([(1, IDLE), (9, FIRE)])
    held = [fr for fr in frames if fr["mask"] == FIRE]
    every_frame = all(fr["cbtnp"] for fr in held)
    print("\nhold fire for 9 frames, watching the console's own btnp")
    return check("console btnp still ignores poked gamepad RAM", every_frame,
                 f"true on {sum(fr['cbtnp'] for fr in held)}/{len(held)} frames of a "
                 f"held mask, so a poked hold reads as a press every frame")


def scenario_both_directions():
    frames = run([(60, LEFT | RIGHT)])
    xs = {fr["x"] for fr in frames}
    print("\nhold left and right together for 60 frames")
    return check("opposed input cancels", xs == {START_X},
                 f"x stayed at {sorted(xs)}")


def scenario_fleet_march():
    """Long enough to reach both screen edges: 18 steps right, then 36 back to the left,
    at 55 frames a step. Costly in frames, free in wall clock - --cli is unthrottled."""
    total = 3100
    frames = run([(total, IDLE)])
    print(f"\nidle for {total} frames, watching the fleet march")

    moved = [(prev, fr) for prev, fr in zip(frames, frames[1:])
             if (fr["fx"], fr["fy"], fr["fdir"], fr["fframe"]) !=
                (prev["fx"], prev["fy"], prev["fdir"], prev["fframe"])]
    off_cadence = [fr["f"] for _, fr in moved if fr["f"] % FLEET_STEP_FRAMES != 0]
    expected_steps = total // FLEET_STEP_FRAMES
    ok = check(f"the fleet changes only every {FLEET_STEP_FRAMES}th frame",
               not off_cadence and len(moved) == expected_steps,
               f"{len(moved)} changes, all on multiples of {FLEET_STEP_FRAMES}"
               if not off_cadence else f"{len(off_cadence)} off-cadence, "
               f"first on frame {off_cadence[0]}")

    ok &= check("the waddle swaps on every step",
                all(fr["fframe"] != prev["fframe"] for prev, fr in moved),
                f"frame toggled on {sum(1 for p, f in moved if f['fframe'] != p['fframe'])}"
                f" of {len(moved)} steps")

    slides = [(p, f) for p, f in moved if f["fy"] == p["fy"]]
    drops = [(p, f) for p, f in moved if f["fy"] != p["fy"]]
    bad_slide = [f["f"] for p, f in slides
                 if f["fx"] - p["fx"] != p["fdir"] * FLEET_STEP_X or f["fdir"] != p["fdir"]]
    ok &= check(f"a plain step moves {FLEET_STEP_X} px in the current direction",
                not bad_slide,
                f"{len(slides)} steps, every one {FLEET_STEP_X} px along fdir"
                if not bad_slide else f"first wrong on frame {bad_slide[0]}")

    bad_drop = [f["f"] for p, f in drops
                if f["fx"] != p["fx"] or f["fy"] - p["fy"] != FLEET_DROP_Y
                or f["fdir"] != -p["fdir"] or p["fx"] not in (0, FLEET_X_MAX)]
    ok &= check("hitting an edge drops one row and reverses, without moving sideways",
                len(drops) >= 2 and not bad_drop,
                f"{len(drops)} drops, on frames {[f['f'] for _, f in drops]} at x "
                f"{[p['fx'] for p, _ in drops]}, y {[f['fy'] for _, f in drops]}"
                if not bad_drop else f"first wrong on frame {bad_drop[0]}")

    ok &= check("both edges reached, and never crossed",
                {p["fx"] for p, _ in drops} == {0, FLEET_X_MAX}
                and min(fr["fx"] for fr in frames) == 0
                and max(fr["fx"] for fr in frames) == FLEET_X_MAX,
                f"fleet x spanned {min(fr['fx'] for fr in frames)}.."
                f"{max(fr['fx'] for fr in frames)}, bounds 0..{FLEET_X_MAX}")
    return ok


def main():
    ok = True
    ok &= scenario_move(LEFT, "left", lambda f: max(X_MIN, START_X - f))
    ok &= scenario_move(RIGHT, "right", lambda f: min(X_MAX, START_X + f))
    ok &= scenario_hold_fire()
    ok &= scenario_tap_fire()
    ok &= scenario_tap_while_in_flight()
    ok &= scenario_both_directions()
    ok &= scenario_console_btnp()
    ok &= scenario_fleet_march()
    print("\nall scenarios passed" if ok else "\nsome scenarios failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
