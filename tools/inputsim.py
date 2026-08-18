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

SCREEN_W, SCREEN_H, SPRITE_W, SPRITE_H = 240, 136, 8, 8
START_X, X_MIN, X_MAX = 116, 0, SCREEN_W - SPRITE_W
PLAYER_Y = 120
PLAYER_LIVES, PLAYER_DEAD_FRAMES = 3, 90
BULLET_SPEED, MUZZLE_X, BULLET_H = 2, 3, 3

ENEMY_BULLET_SPEED, ENEMY_BULLET_H, ENEMY_BULLET_MAX = 2, 3, 3
ENEMY_FIRE_FRAMES, ENEMY_MUZZLE_X = 25, 3

FLEET_COLS, FLEET_ROWS = 11, 5
FLEET_COL_SPACING, FLEET_ROW_SPACING = 16, 10
FLEET_COUNT = FLEET_COLS * FLEET_ROWS
FLEET_WIDTH = (FLEET_COLS - 1) * FLEET_COL_SPACING + SPRITE_W
FLEET_START_X, FLEET_START_Y = (SCREEN_W - FLEET_WIDTH) // 2, 20
FLEET_X_MAX = SCREEN_W - FLEET_WIDTH
FLEET_STEP_X, FLEET_DROP_Y = 2, 6
FLEET_STEP_FRAMES_MAX, FLEET_STEP_FRAMES_MIN = 55, 2
FLEET_ROW_POINTS = [30, 20, 20, 10, 10]
FLEET_LANDING_Y = PLAYER_Y - SPRITE_H

BUNKER_COUNT, BUNKER_COLS, BUNKER_ROWS, BUNKER_CELL = 4, 11, 8, 2
BUNKER_W, BUNKER_H = BUNKER_COLS * BUNKER_CELL, BUNKER_ROWS * BUNKER_CELL
BUNKER_PITCH = SCREEN_W // BUNKER_COUNT
BUNKER_MARGIN = (BUNKER_PITCH - BUNKER_W) // 2
BUNKER_Y = 100
BUNKER_X = [BUNKER_MARGIN + i * BUNKER_PITCH for i in range(BUNKER_COUNT)]
BUNKER_SHAPE = ("..#######..", ".#########.", "###########", "###########",
                "###########", "###########", "####...####", "###.....###")
BUNKER_FULL = sum(row.count("#") for row in BUNKER_SHAPE)

# game.lua's per-frame trace, in order, each field beside the pattern that matches it.
# One list rather than a name tuple next to a regex literal: the two could drift, and when
# M4 added fields to the probe they did - the regex still ended at r5 and every scenario
# failed on the parse rather than on anything it was testing.
NUM, FLAG, WORD = r"-?\d+", r"\d", r"\w+"
TRACE = (
    (("f", NUM), ("mask", NUM), ("x", NUM), ("live", FLAG), ("by", NUM), ("bx", NUM),
     ("cbtnp", FLAG), ("fx", NUM), ("fy", NUM), ("fdir", NUM), ("fframe", FLAG),
     ("score", NUM))
    + tuple((f"r{row}", NUM) for row in range(1, FLEET_ROWS + 1))
    + (("state", WORD), ("lives", NUM), ("dtimer", NUM))
    + tuple(field for slot in range(1, ENEMY_BULLET_MAX + 1)
            for field in ((f"e{slot}", FLAG), (f"e{slot}x", NUM), (f"e{slot}y", NUM)))
    + tuple((f"b{b}r{row}", NUM) for b in range(1, BUNKER_COUNT + 1)
            for row in range(1, BUNKER_ROWS + 1)))

FIELDS = tuple(name for name, _ in TRACE)
FRAME_RE = re.compile(r"\[" + " ".join(f"({pat})" for _, pat in TRACE) + r"\]")

# Rows are traced as a bitmask, one bit per column, so a scenario can say which invader
# died rather than only how many.
ROWS = tuple(f"r{row}" for row in range(1, FLEET_ROWS + 1))
SLOTS = tuple(f"e{slot}" for slot in range(1, ENEMY_BULLET_MAX + 1))


def value(text):
    """game.state is a word; every other field is an integer."""
    return int(text) if text.lstrip("-").isdigit() else text


def popcount(mask):
    return bin(mask).count("1")


def columns(mask):
    """The 1-based fleet columns a row mask has set."""
    return [col for col in range(1, FLEET_COLS + 1) if mask & (1 << (col - 1))]


def row_count(frame, row):
    """How many invaders are left in `row`, 1-based."""
    return popcount(frame[ROWS[row - 1]])


def step_frames(alive):
    """game.lua's fleet_step_frames(), mirrored."""
    span = FLEET_STEP_FRAMES_MAX - FLEET_STEP_FRAMES_MIN
    return FLEET_STEP_FRAMES_MIN + (alive - 1) * span // (FLEET_COUNT - 1)


def living(frame):
    return sum(popcount(frame[r]) for r in ROWS)


def bunker_cells(frame, bunker):
    """The (col, row) cells still standing in `bunker`, 1-based, read off its row masks."""
    return {(col, row)
            for row in range(1, BUNKER_ROWS + 1)
            for col in range(1, BUNKER_COLS + 1)
            if frame[f"b{bunker}r{row}"] & (1 << (col - 1))}


def bunker_live(frame, bunker=None):
    """Cells left in one bunker, or across all four."""
    which = (bunker,) if bunker else range(1, BUNKER_COUNT + 1)
    return sum(len(bunker_cells(frame, b)) for b in which)


def cell_box(bunker, col, row):
    """The screen box of one cell: (x, y, x_end, y_end), ends exclusive."""
    x = BUNKER_X[bunker - 1] + (col - 1) * BUNKER_CELL
    y = BUNKER_Y + (row - 1) * BUNKER_CELL
    return x, y, x + BUNKER_CELL, y + BUNKER_CELL


def bunker_at(x, width=1):
    """Which bunker a box of `width` px starting at `x` overlaps, or None. The gaps are
    wide enough that a bullet cannot straddle two."""
    for b, bx in enumerate(BUNKER_X, start=1):
        if x < bx + BUNKER_W and x + width > bx:
            return b
    return None


def expected_blast(live, col, row):
    """game.lua's erode_bunker(), mirrored: the plus around (col, row), clipped to the grid
    and intersected with what was still standing."""
    return {(col + dc, row + dr) for dc, dr in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
            if 1 <= col + dc <= BUNKER_COLS and 1 <= row + dr <= BUNKER_ROWS} & live


def facing_cell(live, cols, from_below):
    """The cell a shot arriving over `cols` meets first - lowest row when it is rising,
    highest when it is falling. This is the rule game.lua's bunker_cell() implements, and
    asserting against it is what makes 'erodes from the right side' testable."""
    facing = [(row, col) for col, row in live if col in cols]
    if not facing:
        return None
    row, col = (max if from_below else min)(facing)
    return col, row


def fires_through_a_gap(name, x):
    """LINT-RULES.md L059: a scenario that shoots into what it believes is empty sky says
    so, against the current geometry. Every M1-M4 scenario that fires does it from x 119 or
    x 3, both of which fall between shields - by luck, not by design - and a shot the
    shields ate would surface as `len(fired) == 6`, reading as the single-bullet rule
    breaking rather than as the aim being wrong."""
    hit = bunker_at(x)
    return check(f"{name} fires into open sky", hit is None,
                 f"muzzle x {x} falls in a gap, shields at {BUNKER_X}" if hit is None else
                 f"muzzle x {x} is under bunker {hit}, which spans "
                 f"{BUNKER_X[hit - 1]}..{BUNKER_X[hit - 1] + BUNKER_W - 1}")


def erosions(frames):
    """(frame, bunker, cells that went) for every frame on which a bunker lost cells. A
    cell that comes back is an error, not a finding - nothing restores a shield mid-wave,
    and a per-bunker count could not have seen it."""
    out = []
    for prev, fr in zip(frames, frames[1:]):
        for b in range(1, BUNKER_COUNT + 1):
            before, after = bunker_cells(prev, b), bunker_cells(fr, b)
            if after - before:
                sys.exit(f"bunker {b} regrew {sorted(after - before)} on frame {fr['f']}")
            if before - after:
                out.append((fr, b, before - after))
    return out


def kills(frames):
    """(frame, row, columns cleared, score delta) for every frame on which a row lost an
    invader. A bit that comes back is an error rather than a finding: nothing in the game
    revives an invader, and the old per-row counts could not have seen it."""
    out = []
    for prev, fr in zip(frames, frames[1:]):
        for row, key in enumerate(ROWS, start=1):
            risen = fr[key] & ~prev[key]
            if risen:
                raise AssertionError(
                    f"row {row} gained invaders in columns {columns(risen)} "
                    f"on frame {fr['f']}")
            gone = prev[key] & ~fr[key]
            if gone:
                out.append((fr, row, columns(gone), fr["score"] - prev["score"]))
    return out


def step_schedule(frames):
    """The frames on which update_fleet() is due to step, reconstructed from the trace.

    The fleet timer advances only while the game is PLAYING and something is alive, so the
    death pause takes the march with it. Both are read off the *previous* frame: the step
    happens inside TIC() before the trace is written, and before the kills of that frame
    are scored, so it is the state and living count the frame started with that decide it.
    """
    due, timer = set(), 0
    for i, fr in enumerate(frames):
        alive = FLEET_COUNT if i == 0 else living(frames[i - 1])
        state = "PLAYING" if i == 0 else frames[i - 1]["state"]
        if state == "PLAYING" and alive:
            timer += 1
            if timer >= step_frames(alive):
                timer = 0
                due.add(fr["f"])
    return due


def fleet_of(frame):
    return (frame["fx"], frame["fy"], frame["fdir"], frame["fframe"])


def enemy_shots(frames):
    """(frame, slot) for every shell that came into existence.

    Per slot rather than per total, and a shell is new when its slot was empty *or* when
    its y jumps back up: update_enemy_bullets() frees a slot and enemy_fire() can refill it
    in the same frame, which leaves `active` set on both frames with two different shells
    behind it. Enemy shells only ever move down, so a rising y is always a new one.
    """
    out = []
    for i, fr in enumerate(frames):
        prev = frames[i - 1] if i else None
        for slot in SLOTS:
            if not fr[slot]:
                continue
            if not prev or not prev[slot] or fr[slot + "y"] < prev[slot + "y"]:
                out.append((fr, slot))
    return out


def enemy_flying(frame):
    return [slot for slot in SLOTS if frame[slot]]


def first_overlap_frame(row):
    """The frame on which a bullet fired on frame 1 first overlaps `row` of a fleet that
    has not stepped yet. Derived rather than hardcoded, so it tracks the constants."""
    top = FLEET_START_Y + (row - 1) * FLEET_ROW_SPACING
    for n in range(1, PLAYER_Y):
        by = PLAYER_Y - BULLET_H - BULLET_SPEED * n
        if by < top + SPRITE_H and by + BULLET_H > top:
            return n
    raise AssertionError(f"a bullet never reaches row {row}")


def run(script, clear_at=0, fleet_at=None, lives=0):
    """Run game.lua under the probe with `script` as [(frames, mask), ...] and return
    a list of per-frame dicts.

    The three forcings are LINT-RULES.md L056 stand-ins for player actions that take too
    many frames to script: clear_at kills every remaining invader on that frame (the shot
    that ends a wave), fleet_at is (frame, x, y) and teleports the fleet (two minutes of
    marching), and lives holds the life count there every frame so a long run outlives the
    threat rather than the fleet (a player who never gets hit).
    """
    probe = open(os.path.join(ROOT, "tools", "input-probe.lua"), encoding="utf-8").read()
    table = "{" + ",".join(f"{{{n},{m}}}" for n, m in script) + "}"
    probe = re.sub(r"local PROBE_SCRIPT = \{\}", f"local PROBE_SCRIPT = {table}", probe)
    probe = re.sub(r"local PROBE_CLEAR = 0", f"local PROBE_CLEAR = {clear_at}", probe)
    probe = re.sub(r"local PROBE_LIVES = 0", f"local PROBE_LIVES = {lives}", probe)
    if fleet_at:
        probe = re.sub(r"local PROBE_FLEET = \{\}",
                       "local PROBE_FLEET = {%d,%d,%d}" % fleet_at, probe)
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
    frames = [dict(zip(FIELDS, map(value, m))) for m in FRAME_RE.findall(text)]
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


def stayed_playing(frames):
    """Every M1-M3 scenario was written when nothing could shoot back, and each assumes
    throughout that the ship is alive and taking input. Since M4 that is a thing to assert
    rather than to hope for: a run the ship dies partway through goes on reporting counts
    and positions, and fails looking like a regression somewhere else entirely."""
    dead = [fr for fr in frames if fr["state"] != "PLAYING"]
    return check("the ship survived the run", not dead,
                 f"state stayed PLAYING for all {len(frames)} frames" if not dead else
                 f"state went {dead[0]['state']} on frame {dead[0]['f']}, "
                 f"for {len(dead)} of {len(frames)} frames")


def fleet_has_landed(frame):
    """Whether the fleet's lowest *living* row has reached the player's row, read off the
    row masks rather than off row 5, which may have been shot away."""
    rows = [row for row in range(1, FLEET_ROWS + 1) if frame[ROWS[row - 1]]]
    return bool(rows) and frame["fy"] + (max(rows) - 1) * FLEET_ROW_SPACING >= FLEET_LANDING_Y


def cleared_the_wave(frames):
    """The third closing assertion, and the only place a game over is not a failure.

    Since M5 the shields keep the sweeping ship alive roughly twice as long - measured at
    5-7 deaths where M4 saw 12 - so it kills 49-53 of the fleet instead of 37-45, and a
    fleet down to its last invaders steps every 2 frames and walks itself onto the player's
    row. The run therefore now sometimes plays the wave to its natural end. That is the
    curve doing exactly what the scenario claims, so requiring outlived_the_threat() here
    would be asserting the ship is bad at its job.

    What is still a failure: a game over that is not a landing, or one that arrives while
    the fleet is still thick - either means the run went blind long before it ended."""
    over = [fr for fr in frames if fr["state"] == "GAME_OVER"]
    died = sum(1 for prev, fr in zip(frames, frames[1:])
               if fr["state"] == "PLAYER_DEAD" and prev["state"] != "PLAYER_DEAD")
    if not over:
        return check("the run played a live game to the end", True,
                     f"{died} death(s) survived over {len(frames)} frames, "
                     f"{living(frames[-1])} invaders still up")
    first = over[0]
    spent = living(first) < FLEET_COUNT // 4
    return check("the run ended by clearing the wave, not by going blind",
                 fleet_has_landed(first) and spent,
                 f"game over on frame {first['f']} of {len(frames)}, the fleet landing at "
                 f"y {first['fy']} with {living(first)} of {FLEET_COUNT} left"
                 if fleet_has_landed(first) and spent else
                 f"game over on frame {first['f']} with {living(first)} invaders up and "
                 f"the fleet at y {first['fy']}, which is no landing")


def outlived_the_threat(frames):
    """The weaker companion to stayed_playing(), for the long runs that keep their lives
    topped up: dying is expected and simulated through, reaching a game over is not - past
    that point nothing moves and the rest of the run measures a still picture."""
    over = [fr for fr in frames if fr["state"] == "GAME_OVER"]
    died = sum(1 for prev, fr in zip(frames, frames[1:])
               if fr["state"] == "PLAYER_DEAD" and prev["state"] != "PLAYER_DEAD")
    return check("the run kept playing to the end", not over,
                 f"{died} death(s) survived over {len(frames)} frames" if not over else
                 f"game over on frame {over[0]['f']}, "
                 f"{len(over)} frames of the run measured nothing")


def scenario_move(mask, label, expect):
    """Emptied fleet, like every M1 scenario here: see scenario_hold_fire."""
    frames = run([(300, mask)], clear_at=1)
    xs = [fr["x"] for fr in frames]
    wrong = [(fr["f"], fr["x"], expect(fr["f"])) for fr in frames
             if fr["x"] != expect(fr["f"])]
    print(f"\nhold {label} for 300 frames")
    ok = check(f"1 px per frame then clamped at {expect(300)}",
               not wrong,
               f"x went {xs[0]} -> {xs[-1]}, every frame matched"
               if not wrong else f"{len(wrong)} mismatches, first {wrong[0]}")
    ok &= stayed_playing(frames)
    return ok


def scenario_hold_fire():
    """The ship parks at x 0 first: from its start at 116 the muzzle sits under fleet
    column 6, so the shot would hit an invader rather than fly off the top, and this
    scenario is about the bullet's full flight.

    Emptied fleet, which is how every M1 scenario here now runs. Parking used to be enough
    on its own, but since M4 the walk out from under the fleet takes 116 frames at 1 px a
    frame and the first shell lands on frame 50 - the ship was being shot on the way, and
    then the single btnp edge of a held FIRE fell inside the death pause and was swallowed,
    so 300 frames of held fire produced no bullet at all. A fleet with nothing alive cannot
    shoot, which is the condition M1 was verified under before the fleet existed.
    """
    frames = run([(120, LEFT), (300, LEFT | FIRE)], clear_at=1)
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
    ok &= fires_through_a_gap("the parked ship", X_MIN + MUZZLE_X)
    ok &= stayed_playing(frames)
    return ok


def scenario_tap_fire():
    """Run against an emptied fleet. The ship has to hold still for this - it is about the
    press, not about where the ship is - and standing still at x 116 since M4 means dying
    under fleet column 6, which freezes input for 90 frames and throws the tap spacing out.
    A fleet with nothing alive cannot fire, which is exactly the condition M1 verified this
    under."""
    taps = 4
    frames = run([(1, FIRE), (79, IDLE)] * taps, clear_at=1)
    fired = shots(frames)
    print(f"\ntap fire {taps} times, spaced 80 frames apart, fleet cleared")
    ok = check("one bullet per press", len(fired) == taps,
               f"{len(fired)} bullet(s) from {taps} presses, on frames "
               f"{[fr['f'] for fr in fired]}")
    ok &= stayed_playing(frames)
    return ok


def scenario_tap_while_in_flight():
    """Parked at the left edge, and against an emptied fleet, for the same reasons as
    scenario_hold_fire: a bullet that hits an invader frees its slot early, and then a
    later tap fires a second bullet legitimately - which would fail this check for a
    reason it is not testing."""
    frames = run([(120, LEFT)] + [(1, LEFT | FIRE), (9, LEFT)] * 6, clear_at=1)
    fired = shots(frames)
    print("\ntap fire 6 times, 10 frames apart, while a bullet is still in flight")
    ok = check("presses during flight are ignored", len(fired) == 1,
               f"{len(fired)} bullet(s) from 6 presses")
    # The most fragile aim in the suite: six taps span exactly 60 frames against a 59-frame
    # flight, so a shield that ate the bullet would free the slot and let a later tap fire
    # legitimately - six bullets, reported as the single-bullet rule breaking. x 0's muzzle
    # clears bunker 1 by 16 px, which is luck until it is asserted.
    ok &= fires_through_a_gap("the parked ship", X_MIN + MUZZLE_X)
    ok &= stayed_playing(frames)
    return ok


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
    """Emptied fleet, for the reason scenario_tap_fire gives: the check is that the ship
    does not move, so it cannot be parked away from the fleet's guns."""
    frames = run([(60, LEFT | RIGHT)], clear_at=1)
    xs = {fr["x"] for fr in frames}
    print("\nhold left and right together for 60 frames, fleet cleared")
    ok = check("opposed input cancels", xs == {START_X}, f"x stayed at {sorted(xs)}")
    ok &= stayed_playing(frames)
    return ok


def scenario_fleet_march():
    """Long enough to reach both screen edges: 18 steps right, then 36 back to the left,
    at 55 frames a step. Costly in frames, free in wall clock - --cli is unthrottled.

    The ship parks at the left edge and the probe holds its lives: since M4 an idle ship
    is a target, and every death freezes the march for 90 frames, so a run this long would
    otherwise end in a game over less than halfway across the screen. The pauses that do
    happen are not suppressed - step_schedule() knows the timer stops with the game.
    """
    total = 4000
    frames = run([(total, LEFT)], lives=PLAYER_LIVES)
    print(f"\npark at the left edge for {total} frames, watching the fleet march")

    moved = [(prev, fr) for prev, fr in zip(frames, frames[1:])
             if fleet_of(fr) != fleet_of(prev)]
    due = step_schedule(frames)
    seen = {fr["f"] for _, fr in moved}
    ok = check("the fleet steps exactly when the timer says, and never otherwise",
               seen == due,
               f"{len(moved)} steps, every one on schedule" if seen == due else
               f"{len(seen - due)} unscheduled, {len(due - seen)} missed; "
               f"first difference on frame {min(seen ^ due)}")

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
    ok &= outlived_the_threat(frames)
    return ok


def scenario_kill_bottom_row():
    """Fully determined: the ship starts with its muzzle under fleet column 6, and the
    fleet's first step is frame 55, so nothing has moved when the bullet arrives. Kept
    shorter than a shell's flight - the first one is fired on frame 25 and would reach the
    ship around frame 50 - so the run stays about the kill."""
    frames = run([(1, FIRE), (39, IDLE)])
    hit = first_overlap_frame(FLEET_ROWS)
    aimed = (START_X + MUZZLE_X - FLEET_START_X) // FLEET_COL_SPACING + 1
    struck = kills(frames)
    print("\nfire once from the start position, into the bottom row")

    ok = check("one invader dies, on the frame the boxes first overlap",
               len(struck) == 1 and struck[0][0]["f"] == hit
               and struck[0][1] == FLEET_ROWS and struck[0][2] == [aimed],
               f"{len(struck)} kill(s), "
               + (f"row {struck[0][1]} column {struck[0][2]} on frame "
                  f"{struck[0][0]['f']}, expected row {FLEET_ROWS} column [{aimed}] on "
                  f"frame {hit}" if struck else "expected 1"))
    if not struck:
        return False

    dead = struck[0][0]
    counts = [row_count(dead, row) for row in range(1, FLEET_ROWS + 1)]
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
    ok &= fires_through_a_gap("the ship at its start position", START_X + MUZZLE_X)
    ok &= stayed_playing(frames)
    return ok


def scenario_score_by_row():
    """MISSION.md's 'score increments by row value', checked per kill rather than in
    aggregate: every drop in a row's population must move the score by that row's value."""
    frames = run([(1, FIRE), (9, IDLE)] * 400, lives=PLAYER_LIVES)
    struck = kills(frames)
    print(f"\ntap fire every 10 frames for {len(frames)} frames, watching the score")

    wrong = [(fr["f"], row, delta) for fr, row, cols, delta in struck
             if len(cols) != 1 or delta != FLEET_ROW_POINTS[row - 1]]
    awarded = sorted({delta for _, _, _, delta in struck})
    ok = check("every kill scores exactly its row's value", struck and not wrong,
               f"{len(struck)} kills, values awarded {awarded}"
               if not wrong else f"{len(wrong)} wrong, first {wrong[0]}")
    ok &= check("kills land in rows of differing value", len(awarded) >= 2,
                f"{len(awarded)} distinct value(s) awarded: {awarded}")

    last = frames[-1]
    left = [row_count(last, row) for row in range(1, FLEET_ROWS + 1)]
    expected = sum((FLEET_COLS - n) * FLEET_ROW_POINTS[i] for i, n in enumerate(left))
    ok &= check("the total is the sum of what died", last["score"] == expected,
                f"score {last['score']}, rows left {left} = {expected} points of kills")
    ok &= fires_through_a_gap("the ship at its start position", START_X + MUZZLE_X)
    ok &= outlived_the_threat(frames)
    return ok


def scenario_speed_up():
    """MISSION.md's difficulty curve: the step interval must follow the living count.
    Firing while sweeping spreads the shots across every column, which is what makes the
    count fall far enough for the curve to have a shape worth checking. A stationary ship
    empties one column and then misses until the fleet drifts.

    Closes with cleared_the_wave() rather than outlived_the_threat(): since M5 the shields
    keep the ship alive long enough that this run sometimes finishes the wave outright, and
    a landing at the end of a nearly-cleared fleet is the curve working, not a blind run.
    """
    script = []
    for i in range(34):
        mask = RIGHT if i % 2 == 0 else LEFT
        script += [(1, mask | FIRE), (9, mask)] * 24
    frames = run(script, lives=PLAYER_LIVES)
    print(f"\nsweep and fire for {len(frames)} frames, watching the step interval")

    start = (FLEET_START_X, FLEET_START_Y, 1, 0)
    steps = [(fr["f"], FLEET_COUNT if i == 0 else living(frames[i - 1]))
             for i, fr in enumerate(frames)
             if fleet_of(fr) != (start if i == 0 else fleet_of(frames[i - 1]))]
    seen = {frame for frame, _ in steps}
    due = step_schedule(frames)

    ok = check("every step lands exactly where the living count says it should",
               seen == due,
               f"{len(steps)} steps over {len(frames)} frames, all on schedule"
               if seen == due else f"{len(seen - due)} unscheduled, {len(due - seen)} "
               f"missed; first difference on frame {min(seen ^ due)}")

    # Gaps spanning a death pause measure the pause, not the interval, so they are left
    # out of the trend: the frame-exact check above has already covered them.
    paused = {fr["f"] for fr in frames if fr["state"] != "PLAYING"}
    gaps = [(b - a, alive) for (a, _), (b, alive) in zip(steps, steps[1:])
            if not paused & set(range(a, b))]
    ok &= check("the interval shrinks as the fleet thins",
                bool(gaps) and gaps[-1][0] < gaps[0][0]
                and living(frames[-1]) < FLEET_COUNT,
                f"{gaps[0][0]} frames a step at {gaps[0][1]} alive, "
                f"{gaps[-1][0]} at {gaps[-1][1]}; "
                f"{FLEET_COUNT - living(frames[-1])} invaders killed")
    ok &= cleared_the_wave(frames)
    return ok


def scenario_empty_fleet():
    """The probe empties the fleet directly (LINT-RULES.md L056): reaching zero through
    the gamepad takes tens of thousands of frames and lands somewhere unreproducible.
    It stands in for the shot that kills the last invader."""
    # Cleared before frame 25, when the fleet would otherwise fire its first shell: a
    # fleet emptied early leaves the whole window quiet, and the scenario is about the
    # guard in update_fleet(), not about dodging.
    cleared, total = 20, 400
    frames = run([(total, IDLE)], clear_at=cleared)
    after = frames[cleared - 1:]
    print(f"\nempty the fleet on frame {cleared}, then run {total - cleared} more frames")

    ok = check("the cart survives a fleet with nothing alive", len(frames) == total,
               f"traced all {len(frames)} frames without erroring")
    ok &= check("nothing is left alive", all(living(fr) == 0 for fr in after),
                f"rows {[row_count(after[-1], row) for row in range(1, FLEET_ROWS + 1)]} "
                f"for {len(after)} frames")

    frozen = {fleet_of(fr) for fr in after}
    would_have = sum(1 for fr in after if fr["f"] % step_frames(FLEET_COUNT) == 0)
    ok &= check("the fleet holds where it is instead of stepping", len(frozen) == 1,
                f"held at {frozen.pop() if len(frozen) == 1 else sorted(frozen)[:3]} "
                f"through {would_have} step(s) it would otherwise have taken")
    ok &= check("the score stops moving with nothing left to hit",
                {fr["score"] for fr in after} == {after[0]["score"]},
                f"score stayed at {after[-1]['score']}")
    ok &= check("an empty fleet stops shooting too",
                not any(fr[slot] for fr in after for slot in SLOTS),
                f"no shell in the air for {len(after)} frames")
    ok &= stayed_playing(frames)
    return ok


def bottom_row(frame, col):
    """The bottom-most living row of `col`, or None. game.lua's bottom_invader()."""
    bit = 1 << (col - 1)
    for row in range(FLEET_ROWS, 0, -1):
        if frame[ROWS[row - 1]] & bit:
            return row
    return None


def muzzle_of(frame, slot):
    """The (col, row) a shell was fired from, read back from where it appeared. Either is
    None if the coordinate does not land on the grid, which is a failure worth seeing
    rather than an index to round off.

    Exact because of the order inside TIC(): the fleet steps, then fires, then the frame is
    traced, and update_enemy_bullets() has already run - so a shell's first traced position
    is its muzzle, against the same frame's fleet origin.
    """
    dx = frame[slot + "x"] - frame["fx"] - ENEMY_MUZZLE_X
    dy = frame[slot + "y"] - frame["fy"] - SPRITE_H
    col = dx // FLEET_COL_SPACING + 1 if dx >= 0 and not dx % FLEET_COL_SPACING else None
    row = dy // FLEET_ROW_SPACING + 1 if dy >= 0 and not dy % FLEET_ROW_SPACING else None
    return col, row


def hits_ship(frame, slot):
    """Whether slot's box overlaps the ship's, the check game.lua's player_hit() makes."""
    x, y = frame[slot + "x"], frame[slot + "y"]
    return (x < frame["x"] + SPRITE_W and x + 1 > frame["x"]
            and y < PLAYER_Y + SPRITE_H and y + ENEMY_BULLET_H > PLAYER_Y)


def scenario_enemy_fire():
    """Left held the whole way: x 0 is out of reach, since the leftmost muzzle is
    fleet.x + 3 and the fleet does not come near the left edge inside this run.

    Out of reach is not the same as safe, though - the walk out from under the fleet takes
    116 frames at 1 px a frame and the first shell lands on frame 50, so the ship is
    usually shot on the way and walks out again after each respawn. Those deaths are
    simulated through rather than avoided: the probe holds the life count, and the pauses
    are excluded from the cadence, which they interrupt without changing.
    """
    total = 2000
    frames = run([(total, LEFT)], lives=PLAYER_LIVES)
    fired = enemy_shots(frames)
    print(f"\nwalk to the left edge and watch the fleet shoot for {total} frames")

    ok = check("the fleet shoots back", len(fired) > FLEET_COLS,
               f"{len(fired)} shells over {len(frames)} frames")
    if not fired:
        return False

    # A death clears the sky and restarts the cooldown, so a gap spanning one measures the
    # pause rather than the fire rate.
    paused = {fr["f"] for fr in frames if fr["state"] != "PLAYING"}
    gaps = sorted({b["f"] - a["f"] for (a, _), (b, _) in zip(fired, fired[1:])
                   if not paused & set(range(a["f"], b["f"]))})
    ok &= check(f"a shell every {ENEMY_FIRE_FRAMES} frames", gaps == [ENEMY_FIRE_FRAMES],
                f"every uninterrupted gap {ENEMY_FIRE_FRAMES} frames"
                if gaps == [ENEMY_FIRE_FRAMES] else f"gaps seen: {gaps}")

    air = [len(enemy_flying(fr)) for fr in frames]
    ok &= check(f"never more than {ENEMY_BULLET_MAX} shells in the air",
                max(air) <= ENEMY_BULLET_MAX,
                f"at most {max(air)} at once, of {ENEMY_BULLET_MAX} slots")
    ok &= check("the slots are reused rather than exhausted", len(fired) > ENEMY_BULLET_MAX,
                f"{len(fired)} shells through {ENEMY_BULLET_MAX} slots")

    falls = sorted({fr[slot + "y"] - prev[slot + "y"]
                    for prev, fr in zip(frames, frames[1:]) for slot in SLOTS
                    if prev[slot] and fr[slot] and fr[slot + "y"] > prev[slot + "y"]})
    ok &= check(f"a shell falls {ENEMY_BULLET_SPEED} px per frame",
                falls == [ENEMY_BULLET_SPEED], f"steps seen: {falls}")
    ok &= check("no shell is left on screen below the bottom edge",
                not any(fr[slot] and fr[slot + "y"] >= SCREEN_H
                        for fr in frames for slot in SLOTS),
                f"every shell freed its slot by y {SCREEN_H}")

    muzzles = [muzzle_of(fr, slot) for fr, slot in fired]
    off_grid = [(fr["f"], fr[slot + "x"], fr[slot + "y"])
                for (fr, slot), (col, row) in zip(fired, muzzles)
                if col is None or row is None
                or not 1 <= col <= FLEET_COLS or not 1 <= row <= FLEET_ROWS]
    ok &= check("every shell leaves an invader's muzzle", not off_grid,
                f"{len(fired)} shells, all on the grid; columns used "
                f"{sorted({col for col, _ in muzzles})}"
                if not off_grid else f"{len(off_grid)} off-grid, first {off_grid[0]}")
    ok &= outlived_the_threat(frames)
    return ok


def scenario_bottom_most_fires():
    """MISSION.md's 'only the bottom-most living invader in a column may fire', which needs
    columns whose bottom row has been shot away before it says anything.

    Two phases: sweep and fire to carve the holes, then park at the left edge and stop
    firing, so nothing dies while the shells are being watched and the row masks the check
    reads are the ones that were true when each shell left.
    """
    carve = []
    for i in range(8):
        mask = RIGHT if i % 2 == 0 else LEFT
        carve += [(1, mask | FIRE), (9, mask)] * 24
    watch = 1200
    frames = run(carve + [(120, LEFT), (watch, IDLE)], lives=PLAYER_LIVES)
    quiet = frames[len(frames) - watch:]
    # Detected over the whole trace and filtered afterwards: a shell already in flight when
    # the watch window opens is not a new one, and reading a muzzle off its mid-air
    # position is how it first got reported as fired from nowhere.
    fired = [(fr, slot) for fr, slot in enemy_shots(frames) if fr["f"] >= quiet[0]["f"]]
    print(f"\ncarve holes for {sum(n for n, _ in carve)} frames, then watch {watch} more")

    # The precondition the conclusion actually needs, not merely "something died": without
    # columns whose bottom row is gone, the bottom-most rule below is satisfied by any fleet
    # that always fires from row 5. Since M5 the shields eat a share of the carve, so a thin
    # carve now fails downstream as "the fleet is not firing from the bottom-most invader",
    # which is the M4 rule being blamed for an M5 change.
    carved = [col for col in range(1, FLEET_COLS + 1)
              if (bottom_row(quiet[-1], col) or FLEET_ROWS) < FLEET_ROWS]
    ok = check("the sweep emptied the bottom of at least two columns", len(carved) >= 2,
               f"{FLEET_COUNT - living(quiet[-1])} invaders killed; columns {carved} have "
               f"lost their bottom row, rows left "
               f"{[row_count(quiet[-1], row) for row in range(1, FLEET_ROWS + 1)]}")
    ok &= check("nothing died while the shells were being watched",
               all(living(fr) == living(quiet[0]) for fr in quiet),
               f"{living(quiet[0])} alive for all {len(quiet)} frames")

    wrong, rows_seen = [], set()
    for fr, slot in fired:
        col, row = muzzle_of(fr, slot)
        rows_seen.add(row)
        if col is None or row != bottom_row(fr, col):
            wrong.append((fr["f"], col, row, bottom_row(fr, col) if col else None))
    ok &= check("every shell comes from the bottom-most living invader of its column",
                fired and not wrong,
                f"{len(fired)} shells, every one from the lowest survivor of its column"
                if not wrong else f"{len(wrong)} wrong "
                f"(frame, col, fired from, lowest alive): {wrong[0]}")
    # Without a shot from a column whose bottom row is gone, the check above is satisfied
    # by any fleet that always fires from row 5, which is what it exists to rule out.
    ok &= check("shells came from more than one row", len(rows_seen) > 1,
                f"rows that fired: {sorted(r for r in rows_seen if r)}")
    ok &= outlived_the_threat(frames)
    return ok


def scenario_player_death():
    """Left and right on alternating frames: the ship jitters between x 115 and 116 and
    stays under the fleet's guns, so it is shot sooner or later, and the input it is given
    is visible in its position every frame it is alive. While it is dying that jitter has
    to stop dead - which is the check, in one run.

    One run because the fleet's aim cannot be predicted: the console seeds math.random from
    the clock, so the frame the ship dies on is different every time (docs/lua-notes.md).
    Everything here is read out of the trace rather than scripted against.

    'Sooner or later' is the whole reason this window is 1800 frames rather than 900. The
    fleet fires every 25 frames at a column it picks at random from eleven, and only a
    shell over x 115..123 can land on the ship, so at 900 frames roughly one run in thirty
    never got hit at all and failed on its own premise - observed 2026-08-17, and nothing to
    do with the shields, which do not cover the ship's box at any x. Doubling the window
    puts that under a thousandth. Every assertion below is windowed on the *first* death, so
    the extra frames cost nothing but wall clock.
    """
    total = 1800
    frames = run([(1, LEFT), (1, RIGHT)] * (total // 2))
    died = [fr for prev, fr in zip(frames, frames[1:])
            if fr["state"] == "PLAYER_DEAD" and prev["state"] == "PLAYING"]
    print(f"\njitter under the fleet for {total} frames and get shot")
    ok = check("standing under the fleet gets the ship killed", bool(died),
               f"first death on frame {died[0]['f']}" if died
               else f"never hit in {total} frames")
    if not died:
        return False

    hit = died[0]["f"]
    # The first death's window only. A ship left under the fleet this long is shot down
    # three times, and every PLAYER_DEAD frame of the run would otherwise be counted as
    # part of one very long pause.
    dying = [fr for fr in frames if hit <= fr["f"] < hit + PLAYER_DEAD_FRAMES]
    death, before = frames[hit - 1], frames[hit - 2]
    ok &= check("the run is long enough to see the ship come back",
                hit + PLAYER_DEAD_FRAMES <= total,
                f"died on frame {hit}, {total - hit} frames left of the run")
    if hit + PLAYER_DEAD_FRAMES > total:
        return False

    killer = [slot for slot in SLOTS if before[slot] and not death[slot]
              and hits_ship(death, slot)]
    ok &= check("a shell reached the ship", bool(killer),
                f"slot {killer[0]} overlapped the ship at "
                f"({death[killer[0] + 'x']}, {death[killer[0] + 'y']}), ship x "
                f"{death['x']}" if killer else "no shell was spent on the ship's box")
    ok &= check("the hit costs a life and starts the timer",
                death["lives"] == PLAYER_LIVES - 1
                and death["dtimer"] == PLAYER_DEAD_FRAMES,
                f"lives {before['lives']} -> {death['lives']}, "
                f"timer {death['dtimer']}")
    ok &= check("the sky is cleared by the death",
                not enemy_flying(death) and not death["live"],
                "no shell and no player bullet left in flight")

    # The frame it dies traces as PLAYER_DEAD too - the state flips at the end of the frame
    # the hit lands on - and the timer is decremented from the frame after, so it reads 90
    # down to 1 and the ship is back on the frame it would have read 0.
    ok &= check(f"the pause lasts {PLAYER_DEAD_FRAMES} frames",
                all(fr["state"] == "PLAYER_DEAD" for fr in dying)
                and [fr["dtimer"] for fr in dying]
                == list(range(PLAYER_DEAD_FRAMES, 0, -1)),
                f"{len(dying)} frames of PLAYER_DEAD, timer "
                f"{dying[0]['dtimer']} down to {dying[-1]['dtimer']}")
    alive_xs = {fr["x"] for fr in frames[:hit - 1]}
    ok &= check("input is frozen while the ship is dying",
                len(alive_xs) > 1 and {fr["x"] for fr in dying} == {death["x"]},
                f"x took {sorted(alive_xs)} while alive and stayed at {death['x']} "
                f"for all {len(dying)} frames of the pause")
    ok &= check("nothing shoots at a ship that is already dead",
                not any(enemy_flying(fr) for fr in dying),
                f"no shell in the air for {len(dying)} frames")
    ok &= check("the fleet holds still through the pause",
                len({fleet_of(fr) for fr in dying}) == 1,
                f"fleet held at {fleet_of(death)}")

    back = frames[hit + PLAYER_DEAD_FRAMES - 1]
    ok &= check("the ship comes back at the centre with a life spent",
                back["state"] == "PLAYING" and back["x"] == START_X
                and back["lives"] == PLAYER_LIVES - 1,
                f"respawned on frame {back['f']} at x {back['x']} with "
                f"{back['lives']} lives")
    return ok


def scenario_out_of_lives():
    """MISSION.md's first way to lose. No lives topping: the run is meant to end.

    6000 frames for the same reason scenario_player_death takes 1800 - three deaths at a
    random column every 25 frames is a long tail, and the third one has to land a further 90
    frames before the run stops or the game over falls outside the window. Observed third
    deaths range from frame 1377 to 3912, and at 4000 that last one failed as `the game
    never ended` with all three deaths correctly counted on the line above."""
    total = 6000
    frames = run([(total, IDLE)])
    deaths = [fr for prev, fr in zip(frames, frames[1:])
              if fr["state"] == "PLAYER_DEAD" and prev["state"] == "PLAYING"]
    over = [fr for fr in frames if fr["state"] == "GAME_OVER"]
    print(f"\nstand still under the fleet for {total} frames until the lives run out")

    ok = check(f"{PLAYER_LIVES} lives, {PLAYER_LIVES} deaths",
               len(deaths) == PLAYER_LIVES
               and [fr["lives"] for fr in deaths] == [2, 1, 0],
               f"{len(deaths)} death(s) on frames {[fr['f'] for fr in deaths]}, "
               f"lives {PLAYER_LIVES} -> {[fr['lives'] for fr in deaths]}")
    if len(deaths) != PLAYER_LIVES:
        return False

    ok &= check("the last life ends the game instead of respawning",
                bool(over) and over[0]["f"] == deaths[-1]["f"] + PLAYER_DEAD_FRAMES,
                f"game over on frame {over[0]['f']}, "
                f"{over[0]['f'] - deaths[-1]['f']} frames after the last hit"
                if over else "the game never ended")
    if not over:
        return False

    ok &= check("game over is where the run stays",
                all(fr["state"] == "GAME_OVER" for fr in over)
                and over[-1]["f"] == frames[-1]["f"],
                f"GAME_OVER for the last {len(over)} frames")
    ok &= check("nothing moves once the game is over",
                len({fleet_of(fr) for fr in over}) == 1
                and len({fr["score"] for fr in over}) == 1
                and not any(enemy_flying(fr) for fr in over),
                f"fleet, score and sky all held for {len(over)} frames")
    return ok


def scenario_fleet_landing():
    """MISSION.md's second way to lose: the fleet reaching the player's row is an instant
    game over, whatever the life count says.

    The probe drops the fleet one row above the landing line (LINT-RULES.md L056), standing
    in for the two minutes of marching it would take to get there - and for the ship's
    three lives, which would run out long before. Placed flush against the right edge so
    the next step has to be the drop.

    What this cannot show is the tie: game.lua reads the landing before the hit, so a frame
    that is both ends the game rather than costing a life. Forcing both onto one frame
    needs a shell placed as precisely as the fleet, and a scenario that manufactures its
    own collision proves the probe works, not the game.
    """
    place, total = 150, 400
    landing_y = FLEET_LANDING_Y - (FLEET_ROWS - 1) * FLEET_ROW_SPACING
    frames = run([(120, LEFT), (total - 120, IDLE)],
                 fleet_at=(place, FLEET_X_MAX, landing_y - FLEET_DROP_Y))
    print(f"\nplace the fleet one drop above the player's row on frame {place}")

    put = frames[place - 1]
    ok = check("the fleet starts one drop short of landing",
               (put["fx"], put["fy"]) == (FLEET_X_MAX, landing_y - FLEET_DROP_Y),
               f"placed at ({put['fx']}, {put['fy']}), landing at fleet y {landing_y}")

    dropped = [fr for prev, fr in zip(frames[place - 1:], frames[place:])
               if fr["fy"] != prev["fy"]]
    ok &= check("the next step is the drop", bool(dropped)
                and dropped[0]["fy"] == landing_y and dropped[0]["fx"] == FLEET_X_MAX,
                f"dropped to fleet y {dropped[0]['fy']} on frame {dropped[0]['f']}, "
                f"without moving sideways" if dropped else "the fleet never dropped")
    if not dropped:
        return False

    landed = dropped[0]
    ok &= check("landing on the player's row ends the game on that frame",
                landed["state"] == "GAME_OVER",
                f"state {landed['state']} on frame {landed['f']}, with the bottom row at "
                f"y {landed['fy'] + (FLEET_ROWS - 1) * FLEET_ROW_SPACING} and the ship at "
                f"y {PLAYER_Y}")
    ok &= check("it ends the game whatever the life count says", landed["lives"] > 0,
                f"{landed['lives']} of {PLAYER_LIVES} lives still in hand, and the game "
                f"is over anyway")

    after = [fr for fr in frames if fr["f"] >= landed["f"]]
    ok &= check("the game stays over", all(fr["state"] == "GAME_OVER" for fr in after)
                and len({fleet_of(fr) for fr in after}) == 1,
                f"GAME_OVER with the fleet held for the last {len(after)} frames")
    return ok


# The ship walks here to stand under bunker 2, whose x range is 79..100: the muzzle lands
# at x 89, in the arch notch, so the first shot has to fall through two dead rows before it
# finds anything. A solid column would be hit on the frame it was fired and never traced.
NOTCH_X = BUNKER_X[1] + 5 * BUNKER_CELL - MUZZLE_X
NOTCH_COL = 6


def bullet_impacts(frames):
    """(frame, bunker, cells cleared, the bullet's last live position) for every player
    bullet that died against a shield."""
    out = []
    for fr, bunker, gone in erosions(frames):
        prev = frames[fr["f"] - 2]
        if prev["live"] and not fr["live"]:
            out.append((fr, bunker, gone, (prev["bx"], prev["by"])))
    return out


def scenario_bunkers_intact():
    """The shields exist, all four of them, before anything has touched one. Emptied fleet
    so the run is quiet and nothing can erode a bunker while it is being counted."""
    frames = run([(60, IDLE)], clear_at=1)
    print("\ncount the shields over 60 quiet frames")
    full = {(col, row)
            for row in range(1, BUNKER_ROWS + 1)
            for col in range(1, BUNKER_COLS + 1)
            if BUNKER_SHAPE[row - 1][col - 1] == "#"}

    wrong = [b for b in range(1, BUNKER_COUNT + 1)
             if bunker_cells(frames[-1], b) != full]
    ok = check(f"{BUNKER_COUNT} shields, every cell of the shape standing", not wrong,
               f"{BUNKER_COUNT} bunkers of {BUNKER_FULL} cells at x {BUNKER_X}, "
               f"y {BUNKER_Y}..{BUNKER_Y + BUNKER_H - 1}"
               if not wrong else f"bunker(s) {wrong} do not match BUNKER_SHAPE")
    ok &= check("nothing erodes a shield nobody shot at", not erosions(frames),
                f"all {BUNKER_FULL * BUNKER_COUNT} cells held for {len(frames)} frames")
    ok &= stayed_playing(frames)
    return ok


def scenario_bunker_blocks_bullet():
    """MISSION.md's 'blocks bullets while cells remain', and the direction the erosion runs
    in. Emptied fleet, so the only thing the bullet can meet is the shield and the only
    thing that can erode one is the ship."""
    walk = START_X - NOTCH_X
    frames = run([(walk, LEFT), (1, FIRE), (90, IDLE)], clear_at=1)
    print(f"\npark the muzzle at x {NOTCH_X + MUZZLE_X} under bunker 2, then fire once")

    ok = check("the ship is standing under a shield",
               bunker_at(frames[walk - 1]["x"] + MUZZLE_X) == 2,
               f"ship x {frames[walk - 1]['x']}, muzzle x {frames[walk - 1]['x'] + MUZZLE_X}"
               f", bunker 2 spans x {BUNKER_X[1]}..{BUNKER_X[1] + BUNKER_W - 1}")

    above = [fr for fr in frames if fr["live"] and fr["by"] + BULLET_H <= BUNKER_Y]
    ok &= check("no bullet gets past the shield", not above,
                f"the bullet never rose above y {BUNKER_Y}" if not above else
                f"bullet reached y {min(fr['by'] for fr in above)}, clear of the band")

    impacts = bullet_impacts(frames)
    ok &= check("the shot stops in the shield and takes cells with it", len(impacts) == 1,
                f"{len(impacts)} impact(s); "
                + (f"bunker {impacts[0][1]}, {len(impacts[0][2])} cells at "
                   f"{sorted(impacts[0][2])}, bullet last at {impacts[0][3]}"
                   if impacts else "the bullet died without eroding anything"))
    if len(impacts) != 1:
        return False

    fr, bunker, gone, (bx, by) = impacts[0]
    before = bunker_cells(frames[fr["f"] - 2], bunker)
    centre = facing_cell(before, {NOTCH_COL}, from_below=True)
    ok &= check("it erodes the shield from underneath",
                centre is not None and gone == expected_blast(before, *centre),
                f"blast centred on the lowest live cell of column {NOTCH_COL}, row "
                f"{centre[1]} - two dead rows of the arch skipped" if centre and
                gone == expected_blast(before, *centre) else
                f"cleared {sorted(gone)}, expected {sorted(expected_blast(before, *centre))}"
                if centre else "no live cell in the bullet's column")
    ok &= check("only the shield it hit loses cells",
                all(bunker_live(fr, b) == BUNKER_FULL
                    for b in range(1, BUNKER_COUNT + 1) if b != bunker),
                f"the other three shields still hold {BUNKER_FULL} cells each")
    ok &= stayed_playing(frames)
    return ok


def scenario_bunker_erodes_progressively():
    """MISSION.md's 'erode progressively', and the far side of 'while cells remain': shots
    into one spot drill a channel, each one biting deeper than the last, until the column
    is gone and the next shot flies through untouched."""
    walk = START_X - NOTCH_X
    # 69 idle frames a shot: once the channel is open a bullet needs ~60 frames to leave
    # the screen, and fire() refuses while one is still in flight.
    frames = run([(walk, LEFT)] + [(1, FIRE), (69, IDLE)] * 10, clear_at=1)
    print(f"\ndrill ten shots into bunker 2 at x {NOTCH_X + MUZZLE_X}")

    impacts = bullet_impacts(frames)
    ok = check("the shield takes several hits before it is holed", len(impacts) >= 3,
               f"{len(impacts)} shots stopped by the shield")
    if len(impacts) < 3:
        return False

    counts = [bunker_live(fr, 2) for fr, _, _, _ in impacts]
    ok &= check("every hit costs cells, and none ever come back",
                all(b < a for a, b in zip([BUNKER_FULL] + counts, counts)),
                f"cells left after each hit: {counts}, from {BUNKER_FULL}")

    depths = [pos[1] for _, _, _, pos in impacts]
    ok &= check("each shot bites deeper than the last",
                all(b < a for a, b in zip(depths, depths[1:])),
                f"impact heights {depths}, rising through the shield")

    through = [fr for fr in frames if fr["live"] and fr["by"] + BULLET_H <= BUNKER_Y]
    ok &= check("once the column is gone a shot passes clean through", bool(through),
                f"a bullet cleared the band on frame {through[0]['f']}, after "
                f"{len(impacts)} hits had opened the channel" if through else
                f"nothing got through in {len(frames)} frames")
    ok &= check("the shield is holed, not flattened",
                bunker_live(frames[-1], 2) > BUNKER_FULL // 2,
                f"{bunker_live(frames[-1], 2)} of {BUNKER_FULL} cells still standing "
                f"around the channel")
    ok &= stayed_playing(frames)
    return ok


def scenario_shell_erodes_bunker():
    """The other direction: MISSION.md has both bullets erode the shields, and an enemy
    shell has to eat into the roof rather than the underside.

    The ship never fires, so every cell lost in this run was taken by a shell and the
    erosion centres can be checked against the top-most survivor of each shell's column.
    Lives are held: the run is about the shields, not about dodging."""
    total = 2500
    frames = run([(total, LEFT)], lives=PLAYER_LIVES)
    print(f"\nnever fire, and watch the fleet shell the shields for {total} frames")

    shell_hits = []
    for fr, bunker, gone in erosions(frames):
        prev = frames[fr["f"] - 2]
        for slot in SLOTS:
            if prev[slot] and not fr[slot] and bunker_at(prev[slot + "x"]) == bunker:
                shell_hits.append((fr, bunker, gone, prev[slot + "x"], prev[slot + "y"]))
                break

    ok = check("shells eat into the shields", len(shell_hits) > BUNKER_COUNT,
               f"{len(shell_hits)} shells absorbed, "
               f"{BUNKER_FULL * BUNKER_COUNT - bunker_live(frames[-1])} cells lost")
    if not shell_hits:
        return False

    ok &= check("no shell erodes a shield from below",
                all(y < BUNKER_Y + BUNKER_H for _, _, _, _, y in shell_hits),
                f"every absorbed shell stopped between y {min(y for *_, y in shell_hits)} "
                f"and {max(y for *_, y in shell_hits)}, inside the band "
                f"{BUNKER_Y}..{BUNKER_Y + BUNKER_H - 1}")

    wrong = []
    for fr, bunker, gone, sx, _ in shell_hits:
        before = bunker_cells(frames[fr["f"] - 2], bunker)
        cols = {col for col in range(1, BUNKER_COLS + 1)
                if sx < cell_box(bunker, col, 1)[2] and sx + 1 > cell_box(bunker, col, 1)[0]}
        centre = facing_cell(before, cols, from_below=False)
        if centre is None or gone != expected_blast(before, *centre):
            wrong.append((fr["f"], bunker, sorted(gone), centre))
    ok &= check("every shell erodes the shield from the top down", not wrong,
                f"all {len(shell_hits)} blasts centred on the highest live cell of the "
                f"shell's column" if not wrong else
                f"{len(wrong)} wrong, first (frame, bunker, cleared, expected centre) "
                f"{wrong[0]}")
    ok &= outlived_the_threat(frames)
    return ok


def scenario_fleet_crushes_bunkers():
    """MISSION.md's 'invaders passing through a bunker erase it' - erase, not erode.

    The probe places the fleet with its bottom row inside the band (LINT-RULES.md L056).
    Marching there takes tens of thousands of frames, the fleet lands four drops later, and
    the ship would be shot down long before; this stands in for that descent. Placed at the
    fleet's own start x so the columns it crushes are the ones the arithmetic below
    predicts, rather than wherever a clock-seeded run had drifted to."""
    # Placed before frame 25, when the fleet fires its first shell: a shell reaches the band
    # around frame 41, and cells it took would otherwise be scored against the crush.
    place, total = 20, 200
    # Bottom row's top edge two cell-rows into the band: deep enough that the crush is
    # unambiguous, still eight rows short of the landing that would end the game.
    crush_y = BUNKER_Y + 2 * BUNKER_CELL - (FLEET_ROWS - 1) * FLEET_ROW_SPACING
    frames = run([(total, IDLE)], fleet_at=(place, FLEET_START_X, crush_y),
                 lives=PLAYER_LIVES)
    print(f"\nplace the fleet's bottom row inside the shields on frame {place}")

    standing = bunker_live(frames[place - 2])
    ok = check("the shields are whole when the fleet arrives",
               standing == BUNKER_FULL * BUNKER_COUNT,
               f"{standing} of {BUNKER_FULL * BUNKER_COUNT} cells standing on frame "
               f"{place - 1}")

    put = frames[place - 1]
    ok &= check("the fleet is standing in the band, and has not landed",
                put["fy"] == crush_y and not fleet_has_landed(put),
                f"fleet at y {crush_y}, bottom row y "
                f"{crush_y + (FLEET_ROWS - 1) * FLEET_ROW_SPACING}, band "
                f"{BUNKER_Y}..{BUNKER_Y + BUNKER_H - 1}, landing at y {FLEET_LANDING_Y}")

    covered = set()
    for row in range(1, FLEET_ROWS + 1):
        iy = put["fy"] + (row - 1) * FLEET_ROW_SPACING
        for col in columns(put[ROWS[row - 1]]):
            ix = put["fx"] + (col - 1) * FLEET_COL_SPACING
            for b in range(1, BUNKER_COUNT + 1):
                for bcol in range(1, BUNKER_COLS + 1):
                    for brow in range(1, BUNKER_ROWS + 1):
                        cx, cy, cx2, cy2 = cell_box(b, bcol, brow)
                        if ix < cx2 and ix + SPRITE_W > cx and iy < cy2 and iy + SPRITE_H > cy:
                            covered.add((b, bcol, brow))

    left = {(b, col, row) for b in range(1, BUNKER_COUNT + 1)
            for col, row in bunker_cells(put, b)}
    ok &= check("every cell an invader is standing in is gone", not (covered & left),
                f"{len(covered)} cells under the fleet, all erased"
                if not (covered & left) else
                f"{len(covered & left)} cells survived an invader, first "
                f"{sorted(covered & left)[0]}")
    ok &= check("the shields are crushed, not wiped", bool(left - covered),
                f"{len(left)} cells left standing outside the fleet's footprint")

    before = {(b, col, row) for b in range(1, BUNKER_COUNT + 1)
              for col, row in bunker_cells(frames[place - 2], b)}
    ok &= check("nothing outside the footprint was touched", before - left == covered & before,
                f"exactly the {len(covered & before)} covered cells went, and nothing else"
                if before - left == covered & before else
                f"{len((before - left) - covered)} cells went that nothing stood in")
    ok &= outlived_the_threat(frames)
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
    ok &= scenario_enemy_fire()
    ok &= scenario_bottom_most_fires()
    ok &= scenario_player_death()
    ok &= scenario_out_of_lives()
    ok &= scenario_fleet_landing()
    ok &= scenario_bunkers_intact()
    ok &= scenario_bunker_blocks_bullet()
    ok &= scenario_bunker_erodes_progressively()
    ok &= scenario_shell_erodes_bunker()
    ok &= scenario_fleet_crushes_bunkers()
    print("\nall scenarios passed" if ok else "\nsome scenarios failed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
