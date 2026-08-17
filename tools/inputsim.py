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

SCREEN_W, SPRITE_W, SPRITE_H = 240, 8, 8
START_X, X_MIN, X_MAX = 116, 0, SCREEN_W - SPRITE_W
PLAYER_Y = 120
BULLET_SPEED, MUZZLE_X, BULLET_H = 2, 3, 3

FLEET_COLS, FLEET_ROWS = 11, 5
FLEET_COL_SPACING, FLEET_ROW_SPACING = 16, 10
FLEET_COUNT = FLEET_COLS * FLEET_ROWS
FLEET_WIDTH = (FLEET_COLS - 1) * FLEET_COL_SPACING + SPRITE_W
FLEET_START_X, FLEET_START_Y = (SCREEN_W - FLEET_WIDTH) // 2, 20
FLEET_X_MAX = SCREEN_W - FLEET_WIDTH
FLEET_STEP_X, FLEET_DROP_Y = 2, 6
FLEET_STEP_FRAMES_MAX, FLEET_STEP_FRAMES_MIN = 55, 2
FLEET_ROW_POINTS = [30, 20, 20, 10, 10]

# game.lua's per-frame trace, in order. Kept as names rather than positional letters
# because the tuple is long enough that an unpacking error would go unnoticed.
FIELDS = ("f", "mask", "x", "live", "by", "bx", "cbtnp",
          "fx", "fy", "fdir", "fframe", "score", "r1", "r2", "r3", "r4", "r5")
FRAME_RE = re.compile(
    r"\[(\d+) (\d+) (-?\d+) (\d) (-?\d+) (-?\d+) (\d) "
    r"(-?\d+) (-?\d+) (-?\d+) (\d) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)\]")

ROWS = ("r1", "r2", "r3", "r4", "r5")


def step_frames(alive):
    """game.lua's fleet_step_frames(), mirrored."""
    span = FLEET_STEP_FRAMES_MAX - FLEET_STEP_FRAMES_MIN
    return FLEET_STEP_FRAMES_MIN + (alive - 1) * span // (FLEET_COUNT - 1)


def living(frame):
    return sum(frame[r] for r in ROWS)


def kills(frames):
    """(frame, row, score delta) for every frame on which a row lost an invader."""
    out = []
    for prev, fr in zip(frames, frames[1:]):
        for row, key in enumerate(ROWS, start=1):
            if fr[key] < prev[key]:
                out.append((fr, row, prev[key] - fr[key], fr["score"] - prev["score"]))
    return out


def first_overlap_frame(row):
    """The frame on which a bullet fired on frame 1 first overlaps `row` of a fleet that
    has not stepped yet. Derived rather than hardcoded, so it tracks the constants."""
    top = FLEET_START_Y + (row - 1) * FLEET_ROW_SPACING
    for n in range(1, PLAYER_Y):
        by = PLAYER_Y - BULLET_H - BULLET_SPEED * n
        if by < top + SPRITE_H and by + BULLET_H > top:
            return n
    raise AssertionError(f"a bullet never reaches row {row}")


def run(script, clear_at=0):
    """Run game.lua under the probe with `script` as [(frames, mask), ...] and return
    a list of per-frame dicts. clear_at kills every remaining invader on that frame."""
    probe = open(os.path.join(ROOT, "tools", "input-probe.lua"), encoding="utf-8").read()
    table = "{" + ",".join(f"{{{n},{m}}}" for n, m in script) + "}"
    probe = re.sub(r"local PROBE_SCRIPT = \{\}", f"local PROBE_SCRIPT = {table}", probe)
    probe = re.sub(r"local PROBE_CLEAR = 0", f"local PROBE_CLEAR = {clear_at}", probe)
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
    frames = [dict(zip(FIELDS, map(int, m))) for m in FRAME_RE.findall(text)]
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
    """The ship parks at x 0 first: from its start at 116 the muzzle sits under fleet
    column 6, so the shot would hit an invader rather than fly off the top, and this
    scenario is about the bullet's full flight. The fleet never reaches x 0 in 420
    frames, so the left edge is clear the whole run."""
    frames = run([(120, LEFT), (300, LEFT | FIRE)])
    fired = shots(frames)
    print("\npark at the left edge, then hold fire for 300 frames")
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
    ok &= check("bullet leaves the muzzle", fired[0]["bx"] == X_MIN + MUZZLE_X,
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
    """Parked at the left edge for the same reason as scenario_hold_fire: a bullet that
    hits an invader frees its slot early, and then a later tap fires a second bullet
    legitimately - which would fail this check for a reason it is not testing."""
    frames = run([(120, LEFT)] + [(1, LEFT | FIRE), (9, LEFT)] * 6)
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
    cadence = step_frames(FLEET_COUNT)
    off_cadence = [fr["f"] for _, fr in moved if fr["f"] % cadence != 0]
    expected_steps = total // cadence
    ok = check(f"the fleet changes only every {cadence}th frame",
               not off_cadence and len(moved) == expected_steps,
               f"{len(moved)} changes, all on multiples of {cadence}"
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


def scenario_kill_bottom_row():
    """Fully determined: the ship starts with its muzzle under fleet column 6, and the
    fleet's first step is frame 55, so nothing has moved when the bullet arrives."""
    frames = run([(1, FIRE), (59, IDLE)])
    hit = first_overlap_frame(FLEET_ROWS)
    struck = kills(frames)
    print("\nfire once from the start position, into the bottom row")

    ok = check("one invader dies, on the frame the boxes first overlap",
               len(struck) == 1 and struck[0][0]["f"] == hit
               and struck[0][1] == FLEET_ROWS and struck[0][2] == 1,
               f"{len(struck)} kill(s), "
               + (f"row {struck[0][1]} on frame {struck[0][0]['f']}, expected row "
                  f"{FLEET_ROWS} on frame {hit}" if struck else "expected 1"))
    if not struck:
        return False

    dead = struck[0][0]
    counts = [dead[r] for r in ROWS]
    ok &= check("only the bottom row thins",
                counts == [FLEET_COLS] * (FLEET_ROWS - 1) + [FLEET_COLS - 1],
                f"rows now {counts}, from {[FLEET_COLS] * FLEET_ROWS}")
    ok &= check(f"the score goes up by the bottom row's {FLEET_ROW_POINTS[-1]}",
                dead["score"] == FLEET_ROW_POINTS[-1] and struck[0][3] == FLEET_ROW_POINTS[-1],
                f"score 0 -> {dead['score']}")
    ok &= check("the hit frees the bullet where it struck, not at the top of the screen",
                dead["live"] == 0 and not any(fr["live"] for fr in frames[hit:])
                and frames[hit - 1]["by"] > 0,
                f"bullet cleared on frame {dead['f']} at y {frames[hit - 1]['by']}, "
                f"idle for the remaining {len(frames) - hit} frames")
    return ok


def scenario_score_by_row():
    """MISSION.md's 'score increments by row value', checked per kill rather than in
    aggregate: every drop in a row's population must move the score by that row's value."""
    frames = run([(1, FIRE), (9, IDLE)] * 400)
    struck = kills(frames)
    print(f"\ntap fire every 10 frames for {len(frames)} frames, watching the score")

    wrong = [(fr["f"], row, delta) for fr, row, n, delta in struck
             if n != 1 or delta != FLEET_ROW_POINTS[row - 1]]
    awarded = sorted({delta for _, _, _, delta in struck})
    ok = check("every kill scores exactly its row's value", struck and not wrong,
               f"{len(struck)} kills, values awarded {awarded}"
               if not wrong else f"{len(wrong)} wrong, first {wrong[0]}")
    ok &= check("kills land in rows of differing value", len(awarded) >= 2,
                f"{len(awarded)} distinct value(s) awarded: {awarded}")

    last = frames[-1]
    expected = sum((FLEET_COLS - last[r]) * FLEET_ROW_POINTS[i]
                   for i, r in enumerate(ROWS))
    ok &= check("the total is the sum of what died", last["score"] == expected,
                f"score {last['score']}, rows left {[last[r] for r in ROWS]} "
                f"= {expected} points of kills")
    return ok


def scenario_speed_up():
    """MISSION.md's difficulty curve: the step interval must follow the living count.
    Firing while sweeping spreads the shots across every column, which is what makes the
    count fall far enough for the curve to have a shape worth checking. A stationary ship
    empties one column and then misses until the fleet drifts."""
    script = []
    for i in range(34):
        mask = RIGHT if i % 2 == 0 else LEFT
        script += [(1, mask | FIRE), (9, mask)] * 24
    frames = run(script)
    print(f"\nsweep and fire for {len(frames)} frames, watching the step interval")

    def fleet_of(fr):
        return (fr["fx"], fr["fy"], fr["fdir"], fr["fframe"])

    start = (FLEET_START_X, FLEET_START_Y, 1, 0)
    timer, mismatches, steps = 0, [], []
    for i, fr in enumerate(frames):
        before = FLEET_COUNT if i == 0 else living(frames[i - 1])
        expected = False
        if before:
            timer += 1
            if timer >= step_frames(before):
                timer, expected = 0, True
        observed = fleet_of(fr) != (start if i == 0 else fleet_of(frames[i - 1]))
        if observed != expected:
            mismatches.append((fr["f"], before, observed, expected))
        if observed:
            steps.append((fr["f"], before))

    ok = check("every step lands exactly where the living count says it should",
               not mismatches,
               f"{len(steps)} steps over {len(frames)} frames, all on schedule"
               if not mismatches else f"{len(mismatches)} off, first "
               f"(frame, alive, seen, wanted) {mismatches[0]}")

    gaps = [(b - a, alive) for (a, _), (b, alive) in zip(steps, steps[1:])]
    ok &= check("the interval shrinks as the fleet thins",
                bool(gaps) and gaps[-1][0] < gaps[0][0]
                and living(frames[-1]) < FLEET_COUNT,
                f"{gaps[0][0]} frames a step at {gaps[0][1]} alive, "
                f"{gaps[-1][0]} at {gaps[-1][1]}; "
                f"{FLEET_COUNT - living(frames[-1])} invaders killed")
    return ok


def scenario_empty_fleet():
    """The probe empties the fleet directly (LINT-RULES.md L056): reaching zero through
    the gamepad takes tens of thousands of frames and lands somewhere unreproducible.
    It stands in for the shot that kills the last invader."""
    cleared, total = 100, 400
    frames = run([(total, IDLE)], clear_at=cleared)
    after = frames[cleared - 1:]
    print(f"\nempty the fleet on frame {cleared}, then run {total - cleared} more frames")

    ok = check("the cart survives a fleet with nothing alive", len(frames) == total,
               f"traced all {len(frames)} frames without erroring")
    ok &= check("nothing is left alive", all(living(fr) == 0 for fr in after),
                f"rows {[after[-1][r] for r in ROWS]} for {len(after)} frames")

    def fleet_of(fr):
        return (fr["fx"], fr["fy"], fr["fdir"], fr["fframe"])

    frozen = {fleet_of(fr) for fr in after}
    would_have = sum(1 for fr in after if fr["f"] % step_frames(FLEET_COUNT) == 0)
    ok &= check("the fleet holds where it is instead of stepping", len(frozen) == 1,
                f"held at {frozen.pop() if len(frozen) == 1 else sorted(frozen)[:3]} "
                f"through {would_have} step(s) it would otherwise have taken")
    ok &= check("the score stops moving with nothing left to hit",
                {fr["score"] for fr in after} == {after[0]["score"]},
                f"score stayed at {after[-1]['score']}")
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
    ok &= scenario_kill_bottom_row()
    ok &= scenario_score_by_row()
    ok &= scenario_speed_up()
    ok &= scenario_empty_fleet()
    print("\nall scenarios passed" if ok else "\nsome scenarios failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
