# PROGRESS.md

Running log for the TIC-80 Space Invaders cartridge. Read `MISSION.md` for what to
build and `AGENTS.md` for how to work; this file records where things actually stand.

**Update rule:** `AGENTS.md` §3 *Keeping `PROGRESS.md` current* governs this file —
which section takes what, and when to write to it. Update as you go, not only at
milestone end. Do not mark a milestone `DONE` without having loaded the cart and
observed the behavior (`AGENTS.md` §3 rule 4, and §6).

---

## 1. Milestone status

Legend: `TODO` · `IN PROGRESS` · `DONE` (verified in-console) · `BLOCKED`

| # | Milestone | Status | Notes |
|---|---|---|---|
| M0 | Skeleton — metadata header, `TIC()`, `cls()`, "HELLO", scaffolding | DONE | Verified 2026-08-16: "HELLO" observed on screen via `tools/screendump.py` — 76 px of color 12 at x 105..133, y 64..68, rest of the screen color 0. 60.01 FPS on the host clock. Lint pass clean. |
| M1 | Player — movement, edge clamp, single bullet | DONE | Verified 2026-08-16 with `tools/inputsim.py`: 1 px/frame both ways, clamped at x 0 and 232, one bullet per press, 6 presses during flight ignored, bullet rises 2 px/frame and frees its slot on frame 60. Ship and bullet observed on screen via `tools/screendump.py`; 60.00 FPS moving and firing. Lint pass clean. The `btnp` caveat below is the one gap. |
| M2 | Fleet — 5 × 11 grid, stepped march, drop-and-reverse, waddle | DONE | Verified 2026-08-17 with `tools/inputsim.py`: 56 steps in 3,100 frames, every one on a multiple of 55, each a 2 px move along the current direction, the waddle toggling on all 56; two drop-and-reverses, at x 72 and x 0, each +6 px in y with no sideways move. Grid observed via `tools/screendump.py` — 55 invaders at x 36..203, y 20..67, three distinct shapes across the five rows — and again at frame 1050, flush right at x 72..239 and one row lower at y 26. 60.00 FPS with the full fleet, moving and firing. Lint pass clean. |
| M3 | Combat — bullet kills, scoring, speed-up curve | DONE | Verified 2026-08-17 with `tools/inputsim.py`, eleven scenarios: a shot from the start position kills the bottom-row invader on frame 25 — the frame the two boxes first overlap — for 10 points, thinning only row 5 and freeing the bullet at y 67 rather than at the top of the screen; over 4,000 frames of tap-firing, all 25 kills scored exactly their own row's value, all three values (10/20/30) occurred, and the total matched the survivors; sweeping and firing for 8,160 frames killed 53 of 55, and all 820 fleet steps landed exactly where the living count says they should, the interval falling from 53 frames to 2. A fleet emptied on frame 100 held still for the next 300 frames without erroring. Kills observed on screen via `tools/screendump.py` — after 600 frames of held fire, 47 invaders left with gaps in all five rows. 60.00 FPS console / 60.04 host, moving and firing. Lint pass clean; L056 added. |
| M4 | Threat — enemy fire, death, lives, game over | DONE | Verified 2026-08-17 with `tools/inputsim.py`, five new scenarios: over 2,000 frames the fleet fired 76 shells, every uninterrupted gap exactly 25 frames, never more than 2 in the air at once, each falling 2 px/frame from a muzzle that landed on the grid in all eleven columns and freeing its slot by y 136; after a sweep had emptied the bottom of several columns, all 44 shells of a quiet 1,200-frame window came from the bottom-most living invader of their column, across four different rows; a ship jittering under the fleet was hit at x 115 by a shell at (115, 118), lost a life, held for exactly 90 frames of `PLAYER_DEAD` with the timer 90 down to 1, ignored the left/right it was still being given, saw no shell fired at it while dying, and came back at x 116 — the fleet frozen at (48, 20) throughout; three deaths spent three lives and the third ran into `GAME_OVER` 90 frames later, where the fleet, score and sky all stopped for the remaining 2,112 frames; and a fleet placed one drop above the player's row dropped to y 72 and ended the game on that same frame with all three lives still in hand. Observed on screen via `tools/screendump.py`: a yellow shell 1 × 3 px at (167, 98..100), the red explosion 22 px filling the ship's cell at x 116..123, y 120..127 with no green ship and no shells left in the sky, and a game over after the last life with 55 invaders standing and no ship drawn. 60.00 FPS console / 60.48 host differential, moving and firing. Lint pass clean; L057 and L058 added. |
| M5 | Bunkers — cell-grid erosion, per-wave reset | DONE | Verified 2026-08-17 with `tools/inputsim.py`, five new scenarios: four shields of 74 cells stand at x 19/79/139/199, y 100..115, and nothing erodes one nobody shot at; a shot into bunker 2's arch notch stops inside the band, skips the two dead rows below it and blasts the plus around the *lowest* live cell of its column, leaving the other three shields untouched; ten shots into the same spot drilled a channel — 74 → 70 → 66 → 62 cells, each impact 4 px higher than the last, the fourth flying clean through on frame 250 with 62 of 74 cells still standing, which is "blocks bullets while cells remain" and its converse in one run; 2,500 frames of never firing had 32 shells absorbed for 93 cells, every one stopping between y 96 and 106 and every blast centred on the *highest* live cell of its column, the mirror of the player's erosion; and a fleet placed with its bottom row inside the band erased all 90 cells under it and exactly those — 212 left standing outside the footprint, nothing touched beyond it. Observed on screen via `tools/screendump.py`: four 22 px arches with their legs, 1,219 px of color 5 being exactly 35 of ship plus 4 × 74 × 4 of cell; and after 500 frames of sweeping fire, bunker 3 chewed to fragments and bunker 4's roof bitten open. 60.00 FPS console / 60.47 host differential with 296 cells drawn a frame, moving and firing. All 17 M1–M4 scenarios re-run and passing, and the full 22 ran clean three times end to end — 101 assertions, 0 failures — after two pre-existing RNG-deadline flakes were found and fixed (§3). Lint pass clean; L059 and L060 added. |
| M6 | Mystery ship — spawn timing, traversal, bonus | TODO | |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | TODO | |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** M5 complete and verified in-console. Four cell-grid shields stand
between the fleet and the player, eroded from below by the ship, from above by the fleet,
and erased outright by an invader standing in one. Nothing is blocked; M6 (the mystery
ship — spawn timing, traversal, bonus scoring) is next.

Two halves of M5, and only one of them is closed. The erosion is done and tested from every
direction `MISSION.md` §3 names. The **per-wave reset is built but undriven**: the shields
are rebuilt by `reset_bunkers()`, which is split from `build_bunkers()` precisely so a wave
can refill the grid without allocating mid-frame (L009), but `WAVE_CLEAR` does not exist
until M7 and `reset_bunkers()` is a `local` the probe cannot reach without instrumenting
the cart (L053). It is carried as an open question below rather than counted as tested.

Three things M6 inherits. The `_ENV` global list has now been unchanged for four milestones
running, which is the mechanical check that no undocumented API call has crept in — M6's UFO
is the first thing since M1 likely to need a new one, so run L011 early rather than at the
close. Every scenario that fires now asserts the geometry it is aiming through (L059), so a
mystery ship crossing the UFO lane will not silently re-aim an existing scenario the way the
shields nearly did. And `cleared_the_wave()` exists because M5 made the sweeping ship
survive twice as long: any long scenario M6 adds should expect a wave that now sometimes
ends itself.

---

## 2. Environment

Verified 2026-08-16 on WSL2 / Ubuntu 26.04 LTS (x86_64).

| Component | State |
|---|---|
| TIC-80 | `/usr/bin/tic80`, version **1.1.2837 (be42d6f)** — installed from the v1.1 GitHub release `.deb` |
| Lua (host-side, for syntax checks only) | `lua5.4` / `luac5.4` at `/usr/bin/` |
| Display | WSLg — `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`; GUI window renders |
| Audio | working; `libpulse0` installed, SDL connects to WSLg's PulseServer at `unix:/mnt/wslg/PulseServer` |
| Repo | https://github.com/olavostauros/stauros-invaders (public), branch `master` |

Verified 2026-08-16, second pass:

| Component | State |
|---|---|
| Cartridge format | **This build is not PRO and refuses text carts.** `load game.lua` fails with "This version only supports binary .png or .tic cartridges. TIC-80 PRO is needed for text files." |
| Console Lua | **Lua 5.3**, from `trace(_VERSION)` in-console. Not the host `lua5.4`. See `docs/lua-notes.md` |
| Headless run | `--cli` works and prints console output to stdout, including `trace()`. Enough to verify load and runtime errors without a window |
| `lua5.3` host binary | not installed; available in the archive as `5.3.6-3` |
| Screenshot tooling | **None exists and none is needed.** `grim` fails ("compositor doesn't support wlr-screencopy-unstable-v1" — WSLg is not wlroots-based, so no Wayland tool will work), and no X11 tool is installed: `import`, `convert`, `xwd`, `ffmpeg`, `scrot`, `maim`, `xdotool` are all absent, as are Python `mss` and `PIL`. `sudo` needs a password, so an agent cannot install one. Superseded by reading VRAM directly — see below |

The documented run loop **does not work on this build**:

```bash
tic80 --fs=. --cmd="load game.lua & run"   # fails: text cart
```

What does work is packing the code into a minimal binary `.tic` first. A `.tic` is
4-byte-header chunks; a cart containing only a `CHUNK_CODE` (type 5) chunk loads and
runs. Header is `byte0 = bank<<5 | type`, `bytes1-2 = size little-endian`, `byte3`
reserved — https://github.com/nesbox/TIC-80/wiki/.tic-File-Format, read 2026-08-16:

```bash
python3 -c 'c=open("game.lua","rb").read(); open("game.tic","wb").write(
  bytes([5, len(c)&0xFF, (len(c)>>8)&0xFF, 0]) + c)'
tic80 --fs=. --cli --skip --cmd="load game.tic & run"
```

Confirmed working 2026-08-16 — printed `cart game.tic loaded!` and ran `BOOT()`. This
is the endorsed workflow as of the 2026-08-16 `pack.py` decision (§3). `.tic` is
gitignored.

Verified 2026-08-16, third pass — the verification harness in `tools/`:

| Check | State |
|---|---|
| Framebuffer readout | `python3 tools/screendump.py` works. VRAM is byte `0x00000`, 240 × 136 4-bit pixels, so `peek4(y * 240 + x)` is a pixel (`docs/tic80-ram.md`). Prints a palette histogram, bounding box, and the occupied region as ASCII |
| Frame rate | `python3 tools/fpscheck.py` works. **60.01 FPS** on the host wall clock, 60.00 by the console's `time()` |
| `trace()` under `--cli` | Output arrives with **no line break between calls** — a multi-line dump comes back as one flat stream, so parse by fixed width, not by lines |
| `exit()` | Returns to the TIC-80 console; it does **not** quit the process. A driving script must kill it, or it hangs until timeout |

Verified 2026-08-16, fourth pass — input simulation:

| Check | State |
|---|---|
| Gamepad via RAM | Works for `btn`. `poke(0x0FF80, mask)` inside `TIC()` is visible to `btn()` on the same frame; the console rewrites the byte each frame, so the probe writes it every frame including zeros |
| `btnp` via RAM | **Does not work.** A poked hold reads as a fresh press on every frame — `btnp(4)` true on all nine frames of a held mask. The previous-state snapshot comes from the real input device, not RAM. `tools/inputsim.py` keeps a standing scenario watching this, so a console upgrade that fixes it gets noticed rather than assumed |
| Scripted scenarios | `python3 tools/inputsim.py` runs seven scenarios against the game's own state and reports pass/fail. `--hold` also added to `screendump.py` and `fpscheck.py` |
| Keystroke injection | Still impossible. WSLg takes input from the Windows side; `xdotool`/`ydotool`/`wtype` are absent and `/dev/uinput` would not reach the compositor anyway |

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3). Note it checks 5.4 against a 5.3 console:

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

- **2026-08-17 — Two M4 scenarios were flaky against the random stream and had been since
  M4; both windows lengthened.** Found by running the suite repeatedly during M5, not caused
  by it — the ship's box at x 115..123 lies wholly inside the 101..138 gap and is shielded
  by nothing at any x, and the shields touch neither the fire cadence nor the column choice.
  `scenario_player_death` went 900 → 1800 frames: the fleet fires every 25 frames at one of
  eleven columns and only a shell over the ship's 8 px box can land, so 900 frames is ~36
  shells and `(10/11)^36` ≈ 3% of runs never got hit, failing on `standing under the fleet
  gets the ship killed` — which reads exactly like M4's death handling breaking. Its
  docstring's claim that the ship was "certain to be shot" was simply false.
  `scenario_out_of_lives` went 4000 → 6000 for the same reason one level up: it needs three
  deaths *plus* the 90-frame pause after the third, and observed third deaths range from
  frame 1377 to 3912 — at 4000 the run counted all three deaths correctly and then failed on
  `the game never ended`, two frames short. Both are windowed on events read out of the
  trace, so only the wall clock changed. This is L058's cost in a form the rule does not
  name: not a scenario that *depends* on the stream, but one that gives it a deadline. Worth
  stating plainly — the suite had two scenarios that failed for their own reasons, and it
  took running it more than once to see either.
- **2026-08-17 — The shields cost the ship nothing and bought it twice the lifespan, which
  broke a scenario by making the game go too well.** `scenario_speed_up` sweeps and fires
  for 8,160 frames; with bunkers absorbing shells it now dies 5–7 times instead of 12, so it
  kills 49–53 of the fleet instead of 37–45, and a fleet down to its last invaders steps
  every 2 frames and walks itself onto the player's row. The run therefore reaches a game
  over in roughly half of all runs — measured at frames 7573, 7784, 7870 and not at all —
  which `outlived_the_threat()` correctly called a blind tail. Confirmed against a
  worktree at M4's commit, where three runs gave 37/45/38 kills and no game over, so this
  is the shields' doing rather than the clock-seeded stream. Rather than shorten the sweep,
  which would have cost the bottom of the curve the scenario exists to measure, the
  scenario closes with a new `cleared_the_wave()`: a game over is accepted only when it *is*
  a landing and the fleet is down to under a quarter. The assertion got stronger, not
  weaker — it now says why the run ended.
- **2026-08-17 — Bunker cells are read before the fleet, and drawn one `rect` each.**
  Order first: once the fleet descends into the band an invader and a live cell can share a
  pixel, but `crush_bunkers()` runs in the update half of the frame, so any cell inside a
  living invader is already gone by the time the bullet is tested — the shield-first test
  can never steal a kill. Drawing second: 296 `rect` calls a frame is the direct reading of
  `MISSION.md` §3's "draw from that table", and run-length merging the intact shape would
  cut that to 40. It was not needed. Measured at 60.00 FPS console / 60.47 host with the
  full fleet and all four shields up, moving and firing — the same differential M4 recorded
  without them. The merge stays unbuilt rather than sitting in the file unjustified.
- **2026-08-17 — `reset_bunkers()` is split from `build_bunkers()` a milestone before
  anything calls it twice.** This is the shape `LINT-RULES.md` L015 forbids — one caller,
  no second in sight — and it survives on a hard constraint rather than on speculation:
  L009 bans a table constructor in the frame path, and `MISSION.md` §3's per-wave reset has
  to run from inside `WAVE_CLEAR`. Allocating in `build_bunkers()` (BOOT only) and filling
  in `reset_bunkers()` is the only split that lets M7 call it without allocating. Logged
  here so a later reviewer does not merge them back on L015 grounds. User's call, taken
  before the work started, against the alternative of one function M7 would have to split.
- **2026-08-17 — The blast is a plus, and it drills rather than shaves.** Measured before
  any Lua was written: clearing rows `r-1, r, r+1` in the impact column takes 6 px of depth
  per hit, so a ship parked in one spot tunnels through a 16 px shield in four shots and
  leaves 62 of 74 cells standing around the channel. The first estimate offered — "~15
  hits" — was the count to clear *all* the cells and badly overstated the shield's
  durability at any one spot; the correction was put to the user with a flat 3-wide blast
  (~8 shots to tunnel) as the alternative. Kept as the plus: the arcade's shields drilled
  the same way, and a narrow channel is a more interesting thing to shoot through than an
  evenly dissolving wall.
- **2026-08-17 — Bunkers at y 100, 11 × 8 cells of 2 px, at x 19/79/139/199.**
  `MISSION.md` §2 puts them at ~106 and calls its coordinates targets to tune. 100 is as
  close to that as leaves clear sky above the ship at 120, and it is what makes the crush
  reachable in real play: the fleet's bottom row overlaps the band from `fleet.y` 56 and the
  game ends at 74, so four drops happen inside it. y 104 would have matched the spec more
  closely and left one. Pitch is `SCREEN_W / 4` with the shape centred in it, which puts 19
  px of margin at both edges and — the load-bearing accident — leaves the ship's start
  muzzle at x 119 inside a 38 px gap, so every M1–M4 scenario that fires still reaches the
  fleet. That is now asserted rather than relied on (L059).
- **2026-08-17 — `ENEMY_FIRE_FRAMES` is 25, not 45, so that the 3-shell cap can bind.**
  User's call, taken before the work started, on a measurement: a bottom-row shell spawns
  at y 68 and despawns at y 136, which is 34 frames of flight, so at a 45-frame cooldown
  the sky was always empty before the next shot was allowed and `ENEMY_BULLET_MAX` was
  dead code. `MISSION.md` §3 fixes the cap at 3 and leaves the cooldown to tuning. At 25
  two shells are commonly airborne and three become reachable late in a wave, when the
  bottom-most survivor of a column is high on screen and its shell has 54 frames to fall.
  Measured after the change: 2 at once with a full fleet, never more than 3.
- **2026-08-17 — The death pause freezes the whole simulation, not just the input.**
  `MISSION.md` §4 says `PLAYER_DEAD` is "explosion, input frozen", which leaves open
  whether the world keeps moving. It does not: `state_player_dead()` draws the fleet
  without stepping it, so the march, the enemy fire and the shells already in the air all
  stop for 90 frames. User's call, on the arcade reading. The alternative — a fleet that
  keeps marching while the ship is dying — also makes the fleet able to land during the
  pause, which would need `fleet_landed()` checked in a second place.
- **2026-08-17 — Landing is read before the hit, and both are read after drawing.**
  `MISSION.md` §3 makes the fleet reaching the player's row an instant game over
  "regardless of remaining lives", so on a frame that is both a landing and a hit the
  landing has to win; `state_playing()` therefore tests `fleet_landed()` first and only
  falls through to `player_hit()`. What is *testable* is the weaker half — a landing with
  three lives in hand still ends the game, which `scenario_fleet_landing` checks. Forcing
  both onto one frame would mean placing a shell as precisely as the fleet, and a scenario
  that manufactures its own collision proves the probe works rather than the game.
- **2026-08-17 — Enemy shells are a fixed pool of three, filled in `BOOT()`.** The cap on
  shots in the air *is* the number of slots, so a list that grows would need the cap
  enforced separately, and `LINT-RULES.md` L009 keeps table constructors out of the frame
  path anyway. Yellow against the player's white so the two directions read apart at a
  glance — confirmed in the framebuffer, 3 px of color 4 against 35 of green.
- **2026-08-17 — `math.random` is seeded from the clock, and `docs/lua-notes.md` said the
  opposite.** The note claiming an identical stream in every process was written from
  three back-to-back runs that agreed byte for byte. They agreed because the seed has
  roughly one-second granularity: four runs launched simultaneously returned the same
  five numbers, and two launched two seconds later agreed with each other and differed
  from those. Six runs spaced three seconds apart gave six different sequences. The doc is
  corrected and `LINT-RULES.md` L058 now forbids leaning on the stream. `game.lua` is
  unaffected — it never seeds and never needed to — but a scenario that re-ran a script
  expecting the same shots had to be rewritten to read the death out of the trace instead.
- **2026-08-17 — M1's input scenarios run against an emptied fleet.** Since M4 the ship is
  shot at from frame 50, and walking out of range takes 116 frames at 1 px a frame, so
  "park at the left edge first" — M3's remedy — no longer works. `clear_at=1` restores
  exactly the conditions M1 was verified under, before the fleet existed. This was found
  the hard way: `scenario_hold_fire` reported *no bullet at all* from 300 frames of held
  fire, because the single `btnp` edge of a held button landed inside a death pause and
  was swallowed. Every scenario now states the state it is measuring in (L057).
- **2026-08-17 — The fleet's step schedule is reconstructed state-aware rather than
  suppressing enemy fire.** The long M2/M3 scenarios now run through real deaths, and the
  fleet timer stops with the game, so `step_schedule()` ticks only on frames that started
  `PLAYING` and with something alive. The alternative — a probe knob that stops the fleet
  firing — would have kept those scenarios testing the M3 game forever, which is the trap
  `LINT-RULES.md` L056 exists to name. Their lives are held instead, so a run that is
  meant to measure 8,160 frames of marching is not cut short by a game over.
- **2026-08-17 — `tools/screendump.py` can wait for a game state instead of a frame
  number.** The explosion and the game-over screen are the first things worth looking at
  that no frame count can reach: the fleet's aim is random, so the ship dies on a different
  frame every run. `--state` dumps the first frame the given state both entered and
  finished — both sides of `TIC()`, because `game.lua` changes state after it has drawn,
  and reading it only at the end dumped the *living* ship on the frame it was hit.
- **2026-08-17 — An emptied fleet holds still; it does not clear the wave.** The M2 note
  above expected M3 to handle the empty fleet "as a wave-clear rather than as a nil check",
  and this does neither: `update_fleet()` returns early when `count` is 0, so the fleet
  that has nothing left to bound its step simply stops. A `WAVE_CLEAR` state means the
  dispatch table, a pause timer, a wave counter and a fleet rebuild, all of which
  `MISSION.md` §8 puts in M7 and §4 defines against a state machine that does not exist
  yet — building it here to avoid a one-line guard is the speculative abstraction
  `AGENTS.md` §5 bans. User's call, taken before the work started. The guard is a real
  branch and is tested: `scenario_empty_fleet` forces it (L056) and watches the fleet sit
  through six steps it would otherwise have taken.
- **2026-08-17 — The step interval is a straight line from 55 frames at 55 alive to 2 at
  1 alive.** `MISSION.md` §3 gives exactly those two endpoints and says "interpolate; tune
  by playing". Nothing here can play, so anything curvier than the line the endpoints
  already fix would be invented rather than tuned. `fleet_step_frames()` is
  `MIN + floor((count - 1) * (MAX - MIN) / (COUNT - 1))`, `math.floor` rather than `//`
  because L005's grep flags integer division and every hit has to be read by hand.
  The line through those two endpoints turns out to be the identity — the interval in
  frames equals the living count for every count from 2 to 55, and 1 alive gives 2 — which
  is the arcade's own mechanism rather than a coincidence: the original moved one invader
  per frame, so a fleet of *n* took *n* frames to update. The formula is kept over a bare
  `count` because the two endpoints are the tunable thing `MISSION.md` §3 names, and
  changing either should not require rediscovering this. Measured across a real thinning:
  53 frames a step at 53 alive, 2 at 2 alive, with all 820 steps of the run landing on the
  frame the formula predicts.
- **2026-08-17 — A kill shortens the interval on the next frame, not the next step.**
  `update_fleet()` keeps its `timer >= N` compare while `N` is now recomputed each frame,
  so a kill that drops the threshold below the timer already accumulated steps
  immediately. The alternative — latching `N` at the start of each interval — would delay
  every acceleration by up to a full interval, which at 55 frames is most of a second and
  is precisely the feedback the criterion calls "visibly accelerates".
- **2026-08-17 — The score is state, not pixels, until M7.** `MISSION.md` §8's acceptance
  is "score increments by row value", which `tools/inputsim.py` now checks per kill against
  `FLEET_ROW_POINTS`. Drawing a bare number would place HUD text that §2 puts in a band
  with a high score and a life counter, all of it M7's, and it would be moved the moment
  the rest of the band arrives. User's call, taken before the work started.
- **2026-08-17 — Collision is a flat 55-box scan, and the bullet cannot tunnel.** Indexing
  the bullet's position into a row and column would be faster and wrong at the seams: the
  10 px row pitch leaves a 2 px gap the arithmetic has to special-case. 55 axis-aligned
  box tests a frame cost nothing measurable — 60.00 FPS with the full fleet, moving and
  firing. Two facts make the flat scan correct rather than merely cheap: a 1 × 3 bullet
  cannot overlap two invaders at a 16 px column and 10 px row pitch, so the scan order is
  free; and the fastest the two can approach is 8 px in a frame (a 6 px fleet drop against
  a 2 px bullet rise) against an 11 px window in which the boxes overlap, so no drop can
  carry an invader past a live bullet.
- **2026-08-17 — Two M1 scenarios re-aimed once the fleet became hittable.** The ship
  starts at x 116 with its muzzle at 119, directly under fleet column 6, so every shot M1
  fired from the start position now kills a bottom-row invader on frame 25.
  `scenario_hold_fire` (which asserts the bullet leaves the *screen*) and
  `scenario_tap_while_in_flight` (whose bullet now frees its slot early, legitimately
  allowing a second shot) would both have failed for reasons they are not testing. Both
  now park at x 0 first, where the fleet does not reach. Worth flagging for M4 and M5:
  a scenario written against an empty screen quietly changes meaning when something is put
  in front of the ship, and it fails in the direction of looking like a regression.
- **2026-08-17 — The fleet turns on the step that would leave the screen, rather than on
  the one after.** `MISSION.md` §3 says the fleet drops and reverses when a live invader
  touches an edge, which leaves open whether the touching step also moves. It does not:
  the step whose horizontal move would cross the edge becomes the drop instead. That
  guarantees the fleet is flush against the edge when it turns — measured at x 0 and
  x 72, the rightmost invader ending on x 239 — where moving first and turning later
  would leave a ragged 0–1 px margin that varies with the living columns.
- **2026-08-17 — Edge detection scans the living columns, and `alive` exists before
  anything can kill.** `MISSION.md` §3 defines the turn by "any *live* invader", so
  bounding the fleet by columns 1 and 11 would be wrong the moment M3 lands and would
  have to be rewritten rather than extended. `game.fleet.alive[row][col]` is a plain
  boolean grid, not a table per invader — 55 tables would buy nothing M2 or M3 needs, and
  `LINT-RULES.md` L009 keeps allocation out of the frame path anyway. The one thing
  deliberately left out is a guard for an *empty* fleet: `live_columns()` returns nil and
  `step_fleet()` would error, which is unreachable while nothing can die, and M3 has to
  handle the empty fleet as a wave-clear rather than as a nil check.
- **2026-08-17 — The step interval is a constant 55 in M2; the curve is M3's.**
  `MISSION.md` §3 wants N driven by the living count, and §8 puts that in M3 with the
  kills that make it observable. Implemented here it would be a formula over a number
  that never changes — untestable, and the speculative abstraction `AGENTS.md` §5 bans.
  55 is the arcade's own value: the original moved one invader per frame, so a full fleet
  stepped once every 55 frames.
- **2026-08-17 — Fleet layout: 16 × 10 px pitch, starting at (36, 20), dropping 6 px.**
  `MISSION.md` §2 gives the coordinates as targets to tune and asks that the horizontal
  travel fit and the bottom row have room to descend. 11 columns on a 16 px pitch span
  168 px, leaving 72 px of travel and centring the fleet at x 36. A 10 px row pitch puts
  the five rows in y 20..67 — clear of the HUD band and the UFO lane — and a 6 px drop
  gives ten drops from the bottom row to the player's row at y 120.
- **2026-08-17 — All invaders drawn in one color (white).** `MISSION.md` §3 asks for
  three visual types, not three colors, and the 1978 original was monochrome behind a
  colored overlay. The three shapes read apart on screen at 8 × 8, confirmed in the
  framebuffer dump, so color is spare — it stays available for M4's explosions and M6's
  mystery ship, where it will mean something.
- **2026-08-16 — Simulate input by writing the gamepad byte in RAM, and substitute
  `btnp` in the probe.** Every milestone from M1 on has acceptance criteria about
  behavior under input, and nothing here can press a key (§2). GAMEPADS is 4 bytes at
  `0x0FF80`, so `btn` is drivable for real. `btnp` is not — the console snapshots the
  previous frame from the real input device, so a poked hold looks like a fresh press
  every frame, which was measured rather than assumed. `tools/input-probe.lua` therefore
  overrides the global `btnp` with an edge detector over the mask it wrote. This tests
  `game.lua` unmodified under the semantics the wiki documents, and the substitution is
  stated everywhere it matters rather than buried: `LINT-RULES.md` L054,
  `docs/tic80-api.md`, §6 below. The alternative — declaring the criterion met by
  reading the source — is what L054 exists to forbid.
- **2026-08-16 — The sprite sheet lives in `game.lua` and is blitted into tile RAM at
  boot.** `pack.py` writes a `CHUNK_CODE` chunk and nothing else, so the cart ships no
  sprite data at all. Teaching `pack.py` to emit a `CHUNK_TILES` from a separate binary
  would have made the sheet a second deliverable that `AGENTS.md` §1 says should not
  exist, and editing sprites would have meant launching the console's editor. Instead
  `SPRITE_SHEET` holds pixel rows as strings and `BOOT()` pokes them in — 64 `poke4`
  calls per sprite, once, never in the frame path (L009). Sprites stay diffable text and
  M2's six invader frames are new table entries, not a new pipeline. Recorded as
  `LINT-RULES.md` L016, because drawing an unblitted id fails silently.
- **2026-08-16 — The ship is 7 px wide inside its 8 px tile.** An 8-wide symmetric shape
  has no centre column, so the muzzle and the 1 px bullet could not agree; at 7 wide the
  barrel sits on column 3 and the bullet leaves from exactly there. Confirmed on screen:
  bullet x 119 with the ship at x 116.
- **2026-08-16 — `--hold` added to `screendump.py` and `fpscheck.py`.** Both were
  measuring an idle cart, which for a game about moving and shooting is the one frame
  that proves least. `AGENTS.md` §6 asks for the worst-case entity count; now it can be
  asked for. M1 measured 60.00 FPS with right-plus-fire held, against 60.03 idle.
- **2026-08-16 — M0's empty section labels and `DEBUG` flag removed.** `-- collision`
  and `-- game state machine` over nothing are placeholders for structure that does not
  exist, which is the speculative abstraction `AGENTS.md` §5 bans; L014 fixes the order
  sections appear in, not that all of them must. The `DEBUG` flag went with its only
  user, the `_VERSION` trace, whose question is now answered in `docs/lua-notes.md`.
  Both come back the moment something needs them. `LINT-RULES.md` L015, amended.
- **2026-08-16 — Still no state dispatcher, and `game.state` now starts at `PLAYING`.**
  Same reasoning as M0's decision below: M1 has exactly one live state and five empty
  stubs would be worse than none. `PLAYING` is simply what the cart now does. The
  dispatch table arrives with the second real state, which is M4 or M7.
- **2026-08-16 — Verify visual acceptance by reading VRAM, not by screenshotting.**
  M0's acceptance is "text visible" and no capture tool works here (§2), which had left
  the milestone stuck a session. TIC-80's framebuffer is just RAM, so `tools/screendump.py`
  appends a probe to a copy of `game.lua`, wraps the cart's own `TIC()`, and dumps every
  pixel through `peek4`. It is *better* than a screenshot for this job — it reports exact
  coordinates and palette indices, which is what catches text drawn in an invisible
  color, and it runs headless in seconds. Recorded as `LINT-RULES.md` L051.
- **2026-08-16 — `tools/` is tracked, not part of gitignored `scratch/`.** The harness
  was written in `scratch/`, which would have thrown it away and made the next agent
  re-derive it — and every milestone M1–M8 has visual acceptance criteria that need it.
  It is scaffolding on the same footing as `pack.py`, so `AGENTS.md` §1's ban on build
  systems still stands; `scratch/` keeps the generated `.lua`/`.tic` intermediates.
- **2026-08-16 — Frame rate is measured windowed and cross-checked against the host
  clock.** Two traps, both of which would have produced a confident wrong answer.
  `--cli` is unthrottled, so its frame rate reflects host CPU, not console pacing. And
  the console's `time()` would be circular if TIC-80 derived it from the frame counter,
  which "60 FPS over 600 frames" could never detect. `tools/fpscheck.py` therefore runs
  windowed and takes a differential of two sample lengths against the host wall clock —
  differential because `exit()` does not end the process and startup adds an unknown
  constant, both of which cancel. The two clocks agree to 0.02 FPS. `LINT-RULES.md` L052.
- **2026-08-16 — Keep a `.lua`→`.tic` packer (`pack.py`) rather than building PRO from
  source.** User's call, given the console rejects text carts (§2). The TIC-80 README
  does sanction `cmake .. -DBUILD_PRO=On`, but that pulls the whole toolchain the
  2026-08-16 decision below avoided, to fix a problem four lines of Python already fix.
  `game.lua` stays the single tracked deliverable; `game.tic` is generated and
  gitignored. This is scaffolding, not a build system — `AGENTS.md` §1 still bars one.
  The footgun it introduces (running a stale `.tic` after editing the `.lua`) is
  checked as `LINT-RULES.md` L050 rather than left to memory.
- **2026-08-16 — Added `LINT-RULES.md` and wired it into `AGENTS.md` §1, §5, §6.**
  `AGENTS.md` stated conventions in prose, which meant every check depended on an agent
  remembering to look. The rules are now numbered, most carry a `grep`/`awk`/`luac`
  command, and §6 requires a clean pass before a milestone closes. §5 *Linting* asks
  each session to extend the file — add a check when a defect gets through, automate a
  **Read** rule when you find a way, and `RETIRED:` rather than delete. IDs are never
  reused or renumbered, since they get cited from here.
- **2026-08-16 — Rewrote `AGENTS.md` §5's comment rules; removed the banner-comment
  mandate.** §5 previously required sections "separated by banner comments", which
  invites `-- ===== CONSTANTS =====`. Sections are now one plain lowercase line
  (`-- constants`). The new §5 *Comments* subsection bans decorative characters,
  narration, notebook-style step-by-step prose, and TODO/NOTE tags, and restates that
  comments explain *why*. Enforced as `LINT-RULES.md` L030–L033.
- **2026-08-16 — `saveid` set in the M0 metadata header, ahead of `pmem` in M7.**
  `pmem` slots are keyed by `saveid`; picking it later would orphan any score already
  saved under the default. Free to set now, expensive to change later.
- **2026-08-16 — No state dispatcher in M0.** `MISSION.md` §4 requires `TIC()` to
  dispatch on state, but M0 has exactly one state and §5 forbids speculative
  abstraction. `STATE` and `game.state` exist; the dispatch table arrives with the
  second real state rather than as five empty stubs.
- **2026-08-16 — Centering uses `print`'s return value, not a hardcoded offset.**
  `print` reports width only by drawing, so `print_centered` draws once at `y = -FONT_H`
  to measure and again in place. Costs one offscreen draw per frame; keeps the layout
  correct if the string changes.
- **2026-08-16 — Corrected §1's repo root** to `/home/tic-80/stauros-invaders`,
  resolving the §6 question. It was wrong in a public repo.
- **2026-08-16 — Added `AGENTS.md` §3 *Keeping `PROGRESS.md` current* to govern this
  file.** `AGENTS.md` referenced `PROGRESS.md` in six places but never defined its
  structure or when to write to it, so "keep it updated" was unenforceable and the six
  section names here were undocumented. That subsection now maps each section to its
  write trigger and states the `DONE`-means-observed and never-delete-a-resolved-question
  rules. Keep the section list here and the table there in sync if either changes.
- **2026-08-16 — Installed TIC-80 from the prebuilt v1.1 `.deb` rather than building
  from source.** There is no `tic80` package in the Ubuntu archive. The release binary
  statically links SDL2 and `ldd` showed no missing libraries, so it runs as-is;
  building from source would have pulled in the full cmake/SDL/ruby/wayland toolchain
  for no benefit at this version. Revisit only if a post-1.1 feature is needed.
- **2026-08-16 — Repo is public, default branch `master`.** Branch name is git's
  default at init; not a deliberate choice, and cheap to rename while history is one
  commit deep.
- **2026-08-16 — `.gitignore` covers `scratch/` and `*.tic` only** (plus editor/OS
  cruft). `game.lua` and `docs/` are tracked deliverables per `AGENTS.md` §1 and §4.4.

---

## 4. API documentation status

`AGENTS.md` §4.1 requires every TIC-80 function's signature to be looked up and
recorded in `docs/tic80-api.md` **before its first use**.

- `docs/tic80-api.md` — created 2026-08-16. Verified from the wiki, with URLs and dates:
  `cls`, `print`, `trace`, the `TIC()` and `BOOT()` callbacks, the SWEETIE-16 palette,
  and the cartridge metadata tags. These are every API call `game.lua` currently makes —
  cross-checked mechanically via `LINT-RULES.md` L011, which lists the cart's globals
  from bytecode.
- `docs/lua-notes.md` — created 2026-08-16. Console reports **Lua 5.3**; 5.4-only forms
  (`<close>`, `<const>`, `warn`, `coroutine.close`) will not load, and host `luac5.4`
  will not catch them because it is a superset.
- `docs/tic80-ram.md` — created 2026-08-16, when the harness started reading VRAM.
  Records the screen region only: byte `0x00000`, 240 × 136 4-bit pixels, two per byte
  low-nibble-first, so `peek4(y * 240 + x)` is a pixel. Notes that `vbank(1)` would
  switch banks under anything reading VRAM, and that `pmem`'s region at `0x14004` gets
  documented when M7 needs it, not before.
- `peek4`, `exit`, and `time` added to `docs/tic80-api.md` 2026-08-16. They are used by
  `tools/`, not by `game.lua`, but `AGENTS.md` §4.1 is about the project and each has a
  gotcha worth having written down: `peek4` addresses by *nibble*, not byte; `exit()`
  runs the rest of the current `TIC()` and returns to the console instead of quitting;
  `time()` is wall-clock from cart start, confirmed against the host clock.
- Two `print` gotchas recorded: its default color 15 is dark navy and invisible on the
  black the game clears to, and it returns the drawn width, which is how text gets
  centered.
- M1 added, 2026-08-16, all verified from the wiki with URLs and dates: `spr`, `rect`,
  `btn`, `btnp`, the player-1 button id table (left 2, right 3, A 4, confirming
  `MISSION.md` §7), and `poke`/`poke4`. `print` and `print_centered` left the cart with
  M0's placeholder text and will be re-verified when the HUD needs them in M7.
- `docs/tic80-ram.md` gained the two regions M1 touches: TILES at `0x4000` and SPRITES
  at `0x6000` (32 bytes per 8 × 8 tile, low nibble the left pixel, so `poke4` sees a
  tile as 64 nibbles in row-major order), and GAMEPADS at `0x0FF80`.
- `docs/lua-notes.md` stdlib list extended: `ipairs`, `tostring`, `string` (including
  the `s:sub()` method form) and `table` all confirmed running in-console.
- M2 added no TIC-80 call, 2026-08-17. Checked mechanically rather than asserted: the
  L011 `_ENV` list is unchanged from M1 — `BOOT`, `TIC`, `btn`, `btnp`, `cls`, `game`,
  `ipairs`, `math`, `poke4`, `rect`, `spr` — so `docs/tic80-api.md` needed no new entry.
  The fleet is 55 more `spr` calls of a signature already recorded.
- M3 added no TIC-80 call either, 2026-08-17, checked the same mechanical way: the L011
  `_ENV` list is still `BOOT`, `TIC`, `btn`, `btnp`, `cls`, `game`, `ipairs`, `math`,
  `poke4`, `rect`, `spr`. Collision, scoring and the step curve are arithmetic over state
  the cart already had, and M3 draws nothing new — the score stays out of the framebuffer
  until M7's HUD (§3), which is also when `print` gets re-verified.
- M4 added no TIC-80 call either, 2026-08-17, checked the same mechanical way: the L011
  `_ENV` list is unchanged for the third milestone running — `BOOT`, `TIC`, `btn`, `btnp`,
  `cls`, `game`, `ipairs`, `math`, `poke4`, `rect`, `spr`. Enemy fire, death, lives and
  both game-over paths are arithmetic and state over the same eleven names; the shells are
  `rect` and the explosion is `spr`, both signatures already recorded. The one new *Lua*
  call is `math.random`, which lives under `math` and belongs in `docs/lua-notes.md` — it
  is recorded there, including a `DISCREPANCY:` correcting this session's own first
  answer about seeding (§3).
- M5 added no TIC-80 call either, 2026-08-17, checked the same mechanical way: the L011
  `_ENV` list is unchanged for the fourth milestone running — `BOOT`, `TIC`, `btn`, `btnp`,
  `cls`, `game`, `ipairs`, `math`, `poke4`, `rect`, `spr`. The shields are `rect`, whose
  signature has been recorded since M1 and which has no optional arguments to get wrong
  (L007); `MISSION.md` §3's ban on faking destruction with sprite swaps is therefore
  satisfied structurally rather than by discipline. `BUNKER_SHAPE` is read with the same
  `s:sub()` method form `blit_sprite_sheet()` already uses, which never reaches `_ENV`.
- The `btnp` entry carries a `DISCREPANCY:` marker per `AGENTS.md` §4.3 — not between
  the docs and the console, but between the console and RAM: `btnp` ignores writes to
  the GAMEPADS region. It is the reason `tools/inputsim.py` supplies its own.

---

## 5. Known bugs

None reproducible as of 2026-08-17. All twenty-two M1–M5 scenarios in `tools/inputsim.py`
pass, and every framebuffer dump matches its milestone's acceptance criteria.

M3's note here — that the fleet could march off the bottom of the screen because nothing
could end the game — is closed: the fleet reaching the player's row is now a game over.

One limit worth stating rather than filing as a bug: `GAME_OVER` has no way out. Nothing
restarts, and the cart sits on the last frame it drew until it is reloaded. The title
screen, the restart and the wave transition are all M7's (`MISSION.md` §8).

---

## 6. OPEN QUESTIONS

Per `AGENTS.md` §4.5: state the question, implement around it under a clearly stated
assumption, and record the assumption here. Mark answered ones `RESOLVED:` with the
answer and its source; do not delete them.

- **OPEN: Do the bunkers actually reset at the start of each wave?** `MISSION.md` §3 says
  they do, and M5 **cannot test it**: there is no wave transition until M7's `WAVE_CLEAR`,
  and `reset_bunkers()` is a `local` that `tools/inputsim.py` cannot reach without putting a
  hook in the cart, which `LINT-RULES.md` L053 forbids. Assumed correct on inspection — it
  is the same loop that fills the grid at boot, and the boot fill *is* verified, all 296
  cells against `BUNKER_SHAPE`. What is untested is only that something calls it at the
  right moment, and in M5 nothing calls it at all beyond `BOOT()`. Closes with M7's wave
  transition, which should assert the shields come back full after a wave that eroded them.
- **OPEN: Is a 74-cell shield that a parked ship drills through in four shots the right
  durability?** Measured rather than felt (§3). Four shots to open a channel is the arcade's
  own behaviour and is deliberate, but whether a shield that yields that fast still reads as
  *cover* during play is a question only playing settles — and the same four shots let the
  fleet's shells through in the other direction, which is the half that decides whether
  hiding behind one is a strategy or a trap. The tunables are one line each: `BUNKER_BLAST`
  (a flat 3-wide blast roughly doubles the shots to tunnel) and `BUNKER_ROWS`. Related to
  the pressure question below — they trade against each other, and neither should be tuned
  without the other in view.
- **OPEN: Is a shell every 25 frames the right amount of pressure, and 90 frames the
  right death pause?** Both are reasoned rather than played. 25 is the number at which
  `MISSION.md` §3's cap of three concurrent shells stops being dead code (§3 above), not a
  number anyone has felt; what is measured is that a ship left standing under the fleet
  dies about every 400 frames, which spends three lives in well under a minute. The pause
  is 90 frames because the arcade freezes on death and 1.5 s reads as a beat rather than a
  hitch — but it is 90 frames during which the fleet does not march, and whether that
  feels like weight or like a stall is a question only playing it settles. Both are named
  constants (`ENEMY_FIRE_FRAMES`, `PLAYER_DEAD_FRAMES`), so either is a one-line change.
- **OPEN: Does the console's own `btnp` hold to one shot per press, under a real
  finger?** Assumed **yes**, on the wiki's documented semantics — `btnp(id)` with `hold`
  and `period` omitted returns true only on the frame a button becomes pressed, and
  `game.lua` omits both deliberately. The assumption cannot be closed here: the gamepad
  RAM that drives `btn` is invisible to `btnp` (§2), so `tools/inputsim.py` substitutes
  an edge-detecting `btnp` of its own. What *is* measured against the console is the
  stronger invariant — six presses during a bullet's flight produced one bullet — so the
  worst case if the assumption is wrong is a stream at the fire rate, never two bullets
  at once. Closable in seconds by a human holding the fire key on a windowed run;
  otherwise it closes when a keystroke-injection route is found.
- **OPEN: Is a 55-frame step at 55 alive the right opening pace?** It is `MISSION.md`
  §3's suggested value and the arcade's own, so it is the best available answer, but at
  2 px every 0.9 s the fleet takes ~33 s to cross an empty screen and the opening minute
  is slow. §3 says to tune by playing, and nothing here can play; the constants are now
  `FLEET_STEP_FRAMES_MAX` and `FLEET_STEP_FRAMES_MIN`. What M3 added is the shape of the
  ramp, measured rather than guessed: the interval in frames is the living count itself
  (§3), so the fleet is still stepping once a second with 50 invaders up and does not reach
  10 frames a step until 10 remain. Almost all of the acceleration is in the last fifth of
  a wave, and the opening is therefore exactly as slow as this question feared. If it does
  drag, the cheap fix is lowering `FLEET_STEP_FRAMES_MAX`, and the next cheapest is bending
  the interpolation off the straight line, in that order. Still carried: the ramp's shape
  is now known, but whether it *feels* right is a question only playing it settles.
- **OPEN: Is 1 px/frame the right ship speed, and 2 px/frame the right bullet?** They
  are `MISSION.md` §3's suggested values, implemented as named constants
  (`PLAYER_SPEED`, `BULLET_SPEED`) so tuning is a one-line change. §3 says to tune by
  playing, which no tool here can do — carried until someone plays it, and worth
  revisiting once the fleet in M2 gives the ship something to aim at.
- **RESOLVED: Does "HELLO" actually render?** **Yes.** Source: `tools/screendump.py`,
  run 2026-08-16, reading the framebuffer through `peek4`. The screen is 32,564 px of
  color 0 and 76 px of color 12, forming legible "HELLO" glyphs in a bounding box of
  x 105..133, y 64..68 — margins 105 left and 106 right, the one-pixel asymmetry being
  the expected `math.floor` in `print_centered`. The answer turned out not to need a
  screenshot tool at all (§3), so the sub-question of which one to install is moot.
- **RESOLVED: Does the cart hold 60 FPS?** **Yes — 60.01 FPS**, host wall clock, via
  `tools/fpscheck.py` on 2026-08-16. This was never written down as an open question but
  was just as unverified as the one above: M0's acceptance criterion says "60 FPS" and
  nothing had measured it.
- **RESOLVED: How should text carts be run, given this build is not PRO?** With
  `pack.py`, per the user's decision on 2026-08-16 (§3). Building PRO from source
  (`cmake .. -DBUILD_PRO=On`, sanctioned by the TIC-80 README) and buying PRO were the
  alternatives considered.
- **RESOLVED: Does `AGENTS.md` §1's stated repo root need correcting?** Yes — corrected
  to `/home/tic-80/stauros-invaders` on 2026-08-16.
- **RESOLVED: Which Lua version does TIC-80 1.1.2837 embed?** **Lua 5.3.** Source:
  `trace(_VERSION)` run in-console 2026-08-16, recorded in `docs/lua-notes.md`. Integer
  division, `goto`, and bitwise operators are available; 5.4-only syntax is not.
