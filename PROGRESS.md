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
| M6 | Mystery ship — spawn timing, traversal, bonus | DONE | Verified 2026-08-18 with `tools/inputsim.py`, six new scenarios: a saucer crosses the lane at y 10..17, entering at x -16 heading right — the first of a game always from the left — carrying one bonus for all 256 frames of the crossing with the wait held at 0 throughout; over an unforced 3,500 frames three intervals were rolled, 1243, 1210 and 999, every one inside the 900..1500 band, the count-down falling exactly one frame at a time and stopping with the game, and each saucer arriving on the frame its own count reached zero; eight complete crossings alternated sides strictly, entered a full 16 px off screen at both ends, moved only ±1 px a frame, ran 256 moving frames whichever side they came from, spanned x -16..239 and -15..240, left the screen rather than parking on it, and carried all four of 50/100/150/300; a ship parked at the left edge tapping fire for 8,996 frames saw 32 crossings and shot 7 down, each scoring exactly the bonus that saucer was carrying, none of them also thinning the fleet, the bullet spent every time and a fresh in-band interval rolled the moment it died; eight invaders left standing produced no saucer across 2,240 playing frames with the timer held at 1049 and never moving, while nine produced one; and of seven deaths, six began with a saucer up, which held its x, its bonus and its liveness across 540 frozen frames and resumed to a crossing still 256 moving frames long. Observed on screen via `tools/screendump.py`: 66 px of color 2 at x 0..15, y 10..16 — exactly the two tiles' lit pixels from `SPRITE_SHEET` — with the non-black bounding box's top moved from y 20 to y 10, beside 2,200 px of white that is the full 55-invader fleet in waddle frame 1 and 1,015 of green that is 35 of ship plus 245 bunker cells of 4; and during a death, 88 px of red being 66 of saucer plus 22 of explosion, with 568 of green accounting for 142 cells and no ship. 59.99 FPS host differential over frames 1,200..2,400, a window measured to hold a full crossing under the same held mask, console 59.998–60.001. All 22 M1–M5 scenarios re-run and passing, and the full 28 ran clean six times end to end — 148 assertions, 0 failures. Lint pass clean; L016, L052 and L059 amended. |
| M7 | Shell — title, game over, wave transitions, HUD, `pmem`, extra life | DONE | Verified 2026-08-18 with `tools/inputsim.py`, six new scenarios: the cart boots on a title screen where the fleet, the score, the sky and the saucer's own wait all hold still through 90 frames — one step a playing fleet would have taken — and A starts a game on the frame it is pressed, 55 invaders at y 20 with 296 bunker cells and three lives; the full loop runs title → play → game over → title → play again in one trace, the landing ending a game that had scored 10, the game over holding everything frozen for 60 frames until A takes it back to the title, and the second game opening at score 0 with the high score of the first still on the HUD; a wave ends in exactly 120 frames of `WAVE_CLEAR` with the timer 120 down to 1 and nothing moving through it, and then arrives whole on one frame — wave 2, 55 invaders at y 26, 296 cells back from the 274 the last wave was won on, the ship recentred, the sky cleared, no saucer up and its wait rolled at 1485 inside the 900..1500 band; the second wave starts a drop lower, marches every 50 frames instead of 55 and fires every 23 instead of 25, each against the curve rather than against "faster"; a game that scored 3,220 was given one extra ship on the frame it reached 1,530 and kept it for 1,279 frames until it was shot down, with no second ship over the 8,332 frames it took the score to 3,220 and none at all in a second game that scored 1,370; and a console handed an empty `pmem` slot scored 10, ended, and a second console launched afterwards read 10 out of the slot on its first frame. Observed on screen via `tools/screendump.py`: the title at 968 px of green across x 24..213 with the HI line and the prompt below it and no entity anywhere; the HUD band inside y 0..6 — SCORE at x 2, HI at 96, LIVES at 160 and three ship sprites at 192, 200 and 208; "WAVE 2" over the held field with all four shields standing and the ship still where it was; and "GAME OVER" in red over a fleet that is still there either side of it, the banner having cleared its own box out of the invaders behind it. 59.998–60.000 FPS console / 60.36 host differential over frames 1,200..2,400 with the HUD's four `print` calls and three extra `spr` calls on top of M6's worst case. All 28 M1–M6 scenarios re-run and passing, and the full 34 ran clean four times end to end — 193 assertions, 0 failures — after three flakes of the suite's own making were found and fixed (§3). Lint pass clean; L008 automated, L010 amended, L061 and L062 added. |
| M8 | Audio and polish — SFX, fleet loop, explosions, perf pass | TODO | |

**Current position:** M7 complete and verified in-console. The game is a game: it opens on
a title screen, plays waves that start lower and press harder than the one before, pauses
between them, gives a ship at 1,500 points, ends when the lives or the sky run out, and
goes back to the title with a high score that outlives the console. M8 — audio and polish —
is all that is left, and it is the first milestone that needs the SFX editor rather than
the framebuffer.

`MISSION.md` §8's acceptance for M7 was "the full loop title → play → game over → title
runs without a restart", and `scenario_full_loop` is that sentence: one trace, four
transitions, all four of them a button press.

The prediction M6 left about the `_ENV` list finally broke, after five milestones of being
wrong the other way. It gained three names at once — `pmem`, `print` and `string` — because
M7 is the first milestone that draws text and the first that writes anything down. `string`
is the interesting one: `s:sub()` has been used since M0 without ever putting the table in
`_ENV`, because a method call on a string goes through the metatable; `string.format` is
what put it there.

**Both undriven resets are now driven, and the open question they left is closed.**
`reset_bunkers()` and `reset_ufo()` are called from `reset_wave()`, which the transition
runs when its pause ends, and `scenario_wave_transition` asserts both: 296 cells back from
the 274 the wave was won on, and no saucer up with a fresh in-band interval on the first
frame of wave 2. `reset_fleet()` joined them, split out of `build_fleet()` for the same
L009 reason.

Two things M8 inherits. **The harness now has to say which game it is measuring** — a game
over is no longer where a run stops, because fire takes it back to the title and the next
press starts another. `games()` and `first_game()` are that slice, L061 is the rule, and
any new scenario that reads a score climbing or a fleet thinning has to use them. And
**`PROBE_ENDLESS` is a forcing that suppresses the game rather than reaching it** (L062):
nine pre-M7 scenarios clear the fleet only to get it out of the way, and an empty sky is no
longer a state the game can be left in. It is sound only because entering `WAVE_CLEAR` sets
a state and a timer and nothing else. If M8 hangs a sound or an animation off that
transition, the forcing has to grow with it or those nine scenarios will quietly start
measuring something else.

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

Verified 2026-08-18, fifth pass — persistence and cart size:

| Check | State |
|---|---|
| `pmem` across sessions | Works. A slot written by one `tic80` process is read back by the next: `scenario_high_score` writes 0 into slot 0 before boot, plays a game worth 10, and a second console launched afterwards reads 10 on its first frame. The header's `-- saveid: STAUROSINVADERS` is what makes this survive an edit to `game.lua` (`docs/tic80-api.md`) |
| Where the save lands | Under `.local/` in the repo, because the console is run with `--fs=.`. Already gitignored; nothing to add, but note that the suite is therefore **stateful across runs** — every scenario that reaches a game over leaves a high score behind, which is why the one scenario that cares forces the slot rather than assuming it |
| Cart size | 32,696 bytes, **49.9% of one bank**. The 64 KB cap is not close, but `scratch/input.lua` is: `tools/inputsim.py` appends its script table to the cart, and a run of 4,320 segments overflowed at 68,507 bytes. Long scenarios buy frames per segment, not segments |
| Font metrics | Measured in-console rather than recalled: every glyph of the default font occupies a **6 px cell, six rows tall**, `fixed` or not, and the small font is 4 px. Recorded under `print` in `docs/tic80-api.md`; `FONT_W` in `game.lua` is that measurement |

Syntax-only fallback, which is **not** a test — label results *syntax verified,
behavior unverified* (`AGENTS.md` §3). Note it checks 5.4 against a 5.3 console:

```bash
luac5.4 -p game.lua
```

---

## 3. Decisions

Newest first. Record the *why*, not just the *what*.

- **2026-08-18 — `add_score()` is the only writer of `game.score`, and that is what makes
  the extra life possible at all.** M6 left a note that the score had acquired a second
  writer; M7 would have given it a third and a fourth (the HUD reads it, `pmem` saves it,
  and the extra life has to watch it cross a line). Funnelling every point through one
  function means the running high score and the once-a-game ship both hang off the same
  three lines, and neither can be missed by a scoring path added later. It also made the
  scenario possible: the award is observable precisely because nothing else can grant a
  life.
- **2026-08-18 — the wave ramp is three independent curves with three floors, not one
  difficulty number.** `MISSION.md` §4 asks for a lower start, a tighter march and a faster
  gun, and the temptation is one `difficulty(wave)` feeding all three. They are kept apart
  because they trade against each other and because each has a different reason to stop:
  the start is capped at y 52 by geometry — a wave whose bottom row opened inside the
  shields would crush them on frame 1 — while the march floors at 30 frames and the gun at
  15 for feel, which is a guess. A shared cap would have hidden the fact that only one of
  the three is derived.
- **2026-08-18 — the step curve's *top* moves per wave and its bottom does not.** A full
  fleet steps every 55 frames in wave 1 and 50 in wave 2; the last invader steps every 2
  frames in both. Lowering the whole line would have made the endgame of wave 5 unplayable
  while barely changing its opening, and one invader is one invader whenever it is met.
- **2026-08-18 — `reset_wave()` and `reset_game()` do not set the state.** They put a fresh
  wave or a fresh game in the tables and leave the state machine to say when it is being
  played, which is what lets `BOOT()` build a whole game and leave it sitting behind the
  title screen without a line that sets `PLAYING` and another that immediately undoes it.
- **2026-08-18 — the wave transition does its work at the end of the pause, not the
  start.** Entering `WAVE_CLEAR` sets a state and a timer and nothing else, so the pause
  draws the field the wave was actually won on — the eroded shields, the ship where it was
  standing — and the new wave arrives whole on one frame. That is also the only reason
  `PROBE_ENDLESS` can be a one-line forcing (L062), and the note to read before hanging
  anything off the transition in M8.
- **2026-08-18 — "no saucer during a wave transition" is read as: not drawn, not updated,
  and gone before the next wave starts.** `MISSION.md` §3 asks that one never be *present*
  during a transition. `state_wave_clear()` draws no saucer and updates none, and
  `reset_wave()` clears it, so nothing is on screen during the pause and no wave opens with
  one. What is not done is despawning it on the frame the wave ends — the flag can still
  read live through a pause nobody can see it in. Doing that would put work into entering
  `WAVE_CLEAR` and cost the forcing above its one line, for a difference no player can
  observe.
- **2026-08-18 — centred text clears a box behind itself.** Found by looking, not by
  reasoning: the first `tools/screendump.py` of a game over came back with "GAME OVER"
  drawn straight through a fleet that had marched down to y 60, both illegible. The fleet
  can be anywhere on the screen when a game ends, so no fixed banner position is safe and
  the fix belongs in the text helper rather than in a coordinate. It clears the text's own
  box plus 2 px, not the full screen width, so the invaders either side of the banner
  survive. This is exactly the failure L051 exists for — a clean run and passing scenarios
  said nothing about it.
- **2026-08-18 — the game over goes back to the title, not straight into a new game.**
  `MISSION.md` §4 says `A` → `TITLE`, and the reason is worth keeping: the score stays on
  screen until someone chooses to leave it. It costs a second press, which is what
  `scenario_full_loop` traces.
- **2026-08-18 — three flakes were the suite's own, and all three were the same mistake.**
  None was in the cart, and all three were a window measured in the wrong clock.
  `scenario_speed_up` failed on an unscheduled fleet step 4,000 frames after the game it
  was measuring had ended — a real step of a real fleet in the *next* game, because a
  script that taps fire walks a game over back to the title and starts another (L061,
  `games()`/`first_game()`). `scenario_title_screen` failed with "the fleet took 0 steps"
  over a window a 90-frame death pause had swallowed whole. And `scenario_wave_difficulty`
  failed with an *empty* list of step gaps: it dropped every gap a pause touched, and a
  400-frame window holds only seven steps, so one death took all of them. The last two have
  the same fix, and it is the one the saucer scenarios already used and this one did not —
  **an interval is a count of playing frames, not of frames**, because every timer in the
  game advances inside `state_playing` and nowhere else. `playing_between()` had said so
  since M6. The exception is the fire timer, which `kill_player()` resets, so its gaps still
  drop the ones that span a death. This is the fourth fixed-deadline flake in the suite's
  history (§3, M5) and the second in a row whose fix was the right clock rather than a
  longer deadline.
- **2026-08-18 — the extra life needed a forced wave clear to be measurable, and the
  measurement says why.** Six unaided games scored 1210, 1420, 1360, 1330, 1470 and 30
  against a threshold of 1500: a sweeping ship does not quite clear wave 1 before the fleet
  lands on it at about ten thousand frames, and one wave holds only 990 points of invaders.
  Killing the last few on frame 8000 (L056) stands in for the shots that finish a wave, and
  the game plays on into wave 2 for a score of 3,000-4,200. The run's *second* game gets no
  such help and is where "nothing is awarded below 1500" is measured. The interesting half
  is the number this produced: **1,500 is more than a wave is worth**, which is an open
  question below rather than a bug.
- **2026-08-18 — `PROBE_LIVES` became a top-up rather than an assignment.** It wrote the
  life count every frame, which meant a life the game *gave* was taken straight back and
  the extra life was invisible to every scenario that could afford to run long enough to
  earn one. Nothing could add a life before M7, so every earlier scenario ran under
  identical behaviour. The assertions still do not read a life count that rises — that
  happens after every death — they read one *above the forcing's own ceiling*, which only
  the game can produce.
- **2026-08-18 — The saucer is 16 px of one composite `spr()`, and that is the first thing
  in the project no lint grep can see.** The width was the user's call, taken before the
  work started: an 8 px saucer would have read as another invader in a different lane. One
  `spr(SPR_UFO, x, y, C_BLACK, 1, 0, 0, UFO_TILES, 1)` rather than two calls, which needed a
  fact no page states outright — the tile sheet is 16 tiles to a row, so ids 9 and 10 are
  adjacent and `w = 2` consumes them in order. Measured rather than read (tile 9 filled with
  color 2, tile 10 with color 3, drawn at the origin; pixel (0,0) came back 2, (8,0) came
  back 3, (0,8) came back 0) and recorded in `docs/tic80-ram.md`. The cost is that **id 10
  appears in no `spr()` call anywhere**, so L016's grep reports clean whether or not it was
  ever blitted; the rule is amended and the pass gained a second grep listing composite
  calls, whose extra ids have to be read by hand.
- **2026-08-18 — The wait counts down and holds its own interval; it is not a count-up
  against a stored threshold.** The file had both idioms and the choice was not obvious.
  `fleet.timer` and `fleet.fire_timer` count *up* because their thresholds live elsewhere
  and are the same every frame; `death_timer` counts *down* because it is a one-shot whose
  value is fixed when it starts. The saucer is the second kind, and counting down collapses
  two fields into one: the rolled interval *is* the timer, so the probe sees the value on
  the frame it was rolled instead of having to reconstruct it across two spawns. That is
  what let `scenario_ufo_interval` collect three readings in 3,500 frames rather than the
  ~7,000 a reading-per-cycle would have needed — and 7,000 frames of a wait that stops
  during death pauses is exactly the RNG-deadline shape this log records twice.
- **2026-08-18 — The bonus is rolled when the saucer enters, not when it is hit.** Both
  score the same. Rolling at entry means the value belongs to *that* saucer, so the probe
  can trace it and a scenario can assert the score rose by the amount the thing on screen was
  carrying — identity rather than quantity (L060). Rolling at the hit would leave only "the
  score went up by something in the table", which cannot tell a correct award from a bonus
  attached to the wrong event. `MISSION.md` §3's table is read literally, with
  `math.random(#UFO_POINTS)`; the arcade's real rule keyed the 300 to the player's 23rd shot,
  and reproducing it was considered and rejected against §1's "feel, not ROM reproduction" —
  it is carried as an open question below instead.
- **2026-08-18 — `dir` doubles as the memory of which side the last saucer came from.**
  `MISSION.md` §3 asks for alternating entry sides, and the flip happens on the way in, so
  one field carries both the direction of travel and the alternation. Initialising it to -1
  in the state literal means the first saucer of every game enters from the left, which is
  deterministic and therefore assertable — a rare thing to get for free in a system this
  much of which is stream-driven (L058).
- **2026-08-18 — The saucer freezes during a death rather than despawning, and the freeze is
  the absence of code.** The user's call. `state_player_dead()` draws it and does not update
  it, exactly as it treats the fleet, so nothing new was written to make it hold still. The
  cost is that a player can bank a saucer: die with one at mid-screen and it is still sitting
  there 90 frames later. The alternative throws away a bonus the player did nothing to lose.
  Because the behaviour is an absence, it is the kind of thing that comes back silently, so
  `scenario_ufo_freezes_on_death` asserts it directly and `scenario_out_of_lives` now
  includes the saucer's x in its "nothing moves once the game is over" set.
- **2026-08-18 — Below nine invaders no saucer is sent, and that rule is quietly holding ten
  scenarios up.** The arcade's own, and it stops the bonus exactly when the player most wants
  it. The accident is worth stating plainly: `count == 0` satisfies `count <= UFO_FLEET_MIN`,
  so **every `clear_at` scenario in the suite is saucer-free by construction** — which is why
  a new entity crossing the sky broke exactly one of 22 existing scenarios instead of ten. It
  also means no saucer scenario can use the suite's standard quiet-screen trick, so all six
  run with a living fleet, a ship under fire, and `outlived_the_threat()` rather than
  `stayed_playing()`. The threshold is a one-line change on its face and is not one.
- **2026-08-18 — No probe knob spawns a saucer; two knobs were added for things buttons
  genuinely cannot reach.** Forcing a spawn was considered and rejected: L056's test is
  whether scripted input can reach the state in reasonable time, and 1,500 frames is 25
  seconds of play and about a second unthrottled. Worse, `MISSION.md` §8's criterion is that
  the saucer *appears on a randomized interval*, so a knob that staged the spawn would have
  deleted the only thing measuring it. What was added instead: `rush`, which caps the wait so
  eight crossings fit in 2,600 frames rather than three minutes, touching nothing about the
  crossing, the side, the bonus or the collision; and `keep`, generalising `clear_at` to
  leave N invaders standing, which is what makes the suppression threshold testable at the
  boundary — eight against nine — rather than only at zero. A placement knob was rejected on
  the ground `scenario_fleet_landing` already states: a scenario that manufactures its own
  collision proves the probe works, not the game, and an off-by-one in the box test survives
  a shot placed dead centre.
- **2026-08-18 — `rush` clamps the timer *before* the cart runs, not after.** Written the
  obvious way first, and it silently destroyed what it was meant to leave alone: clamping
  after `_TIC()` overwrites every rolled interval with the clamp value, so the traced roll is
  never the cart's own and the 15-to-25-second band has nothing to be checked against.
  Clamping first leaves the roll visible on the frame it was made. The general shape is worth
  keeping in view — a forcing that runs after the code under test does not merely add a
  constraint, it overwrites evidence.
- **2026-08-18 — The scenario script is a Lua table inside the cart, and that is a hard
  budget nobody had hit before.** `scenario_ufo_shot_down` was first written as
  `[(1, FIRE), (1, IDLE)] * 4440` — one segment per frame, the shape every earlier scenario
  uses — and `pack.py` refused it: 88,624 bytes against the 65,535-byte single-bank limit.
  The fix is not compression but a coarser script: the bullet lives 59 frames and `fire()`
  refuses while it is up, so one press every 60 frames produces exactly the same shots at a
  thirtieth of the segments. Measured rather than reasoned — eight presses 60 frames apart
  produced eight bullets, at frames 117, 177, 237 and so on. `SHOT_PERIOD` is now a named
  constant. Any future scenario much past 3,000 frames of alternating masks will hit this.
- **2026-08-18 — Two scenario assertions were written against the frame's own traced state
  and had to be moved to its predecessor.** `scenario_ufo_crossings` first failed on "it
  moves at one speed" (deltas -1, 0, 1) and "every crossing is 256 frames" (lengths 256 and
  346) — both were the death-pause freeze working correctly, being read as a stall. The cart
  changes state *after* it has drawn, so the last frame of a pause is already traced as
  `PLAYING` though `state_player_dead()` ran it. Whether a frame moved anything is decided by
  the state it *started* in, which is the previous frame's trace. `step_schedule()` had
  documented exactly this since M3; it needed applying twice more.
- **2026-08-18 — `tools/screendump.py` needs a life count as well as a gate.** `--ufo` waits
  for the saucer to be wholly on screen, the same class of gate as `--state` and for the same
  reason — the spawn frame is random, so no `--frames` value reaches it. But an idle ship
  spends its three lives somewhere in the first few thousand frames, and `GAME_OVER` is a
  state `update_ufo()` never runs in, so the gate would have waited past the end of the game.
  `--lives` pins the count, borrowed from `tools/input-probe.lua`, which had needed it since
  M3 for the same reason one level down.
- **2026-08-18 — `--hold` cannot reach a worst case that arrives on a timer, which is a gap
  in L052 rather than in this milestone.** The rule's premise is that a gamepad mask puts the
  busiest frame on screen; that holds for a ship, a bullet and a fleet, and fails for a saucer
  that comes 900 to 1,500 frames in and crosses in 256. `fpscheck.py`'s default 300/1200
  samples can contain none of it, and the differential would then report a frame rate for a
  screen the saucer was never on. `--samples` moves the window; the measurement was taken at
  1,200..2,400 and, separately, three runs under the same held mask confirmed a full 256-frame
  crossing falls inside it. The rule is amended to say so.

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
- M6 added no TIC-80 call either, 2026-08-18, checked the same mechanical way and this time
  against a prediction: `PROGRESS.md` had M6 down as the first milestone since M1 likely to
  need one. It did not. The L011 `_ENV` list is unchanged for the fifth milestone running —
  `BOOT`, `TIC`, `btn`, `btnp`, `cls`, `game`, `ipairs`, `math`, `poke4`, `rect`, `spr`. The
  saucer is a `spr` and its bonus a `math.random`, both recorded. L011 was run *before* the
  code was written rather than at the close, per M5's note, which is what makes this a
  measurement rather than a claim.
- Two facts were nevertheless new, and both were looked up before first use per §4.1. The
  **tile sheet is 16 tiles to a row**, which `spr`'s `w`/`h` composite block is laid out
  against — no page states it outright, so it was measured on the framebuffer and written
  into `docs/tic80-ram.md`. And `math.random` has a **two-argument form**, `math.random(m, n)`
  for an integer in `m..n`; `docs/lua-notes.md` had listed only the other two and its silence
  read as an absence. Confirmed in-console (`math.random(900, 1500)` returned 1142 and 1087)
  and recorded there.
- `spr`'s composite path is exercised for the first time in M6, so its wiki entry is now
  measured rather than only read: the "left-to-right from `id`" claim was confirmed on the
  framebuffer, and the two tiles land horizontally adjacent with nothing bleeding into the
  row below.
- The `btnp` entry carries a `DISCREPANCY:` marker per `AGENTS.md` §4.3 — not between
  the docs and the console, but between the console and RAM: `btnp` ignores writes to
  the GAMEPADS region. It is the reason `tools/inputsim.py` supplies its own.

---

## 5. Known bugs

None reproducible as of 2026-08-18. All twenty-eight M1–M6 scenarios in `tools/inputsim.py`
pass — 148 assertions, six clean runs end to end — and every framebuffer dump matches its
milestone's acceptance criteria.

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

- **RESOLVED 2026-08-18: Do the bunkers and the saucer actually reset at the start of each
  wave?** **Yes, and it is now measured rather than inspected.** M7's `WAVE_CLEAR` gave
  both resets a caller: `reset_wave()` runs `reset_fleet()`, `reset_bunkers()`,
  `reset_ufo()` and `clear_bullets()` on the frame the transition's pause runs out.
  `scenario_wave_transition` in `tools/inputsim.py` chews a shield open, empties the fleet,
  and reads the first frame of wave 2 off the trace: 296 cells back from the 274 the wave
  was won on, no saucer up, its wait rolled at 1485 inside the 900..1500 band, the sky
  cleared and the ship recentred. The question below it — the original, kept per the rule
  that answered questions are marked rather than deleted — is what this replaces.
- **OPEN (superseded by the entry above, kept as the record of what was once unknown): Do
  the bunkers and the saucer actually reset at the start of each wave?**
  `MISSION.md` §3 says the shields reset per wave and that the saucer is never present during
  a wave transition, and neither M5 nor M6 **can test it**: there is no wave transition until
  M7's `WAVE_CLEAR`, and `reset_bunkers()` and `reset_ufo()` are `local`s that
  `tools/inputsim.py` cannot reach without putting a hook in the cart, which
  `LINT-RULES.md` L053 forbids. Both assumed correct on inspection, and both boot paths *are*
  verified — all 296 cells against `BUNKER_SHAPE`, and the saucer's first interval rolled
  in-band on frame 1. What is untested in each case is only that something calls it at the
  right moment, and nothing does beyond `BOOT()`. Widened from the shields alone on
  2026-08-18, when `reset_ufo()` joined them. Closes with M7's wave transition, which should
  assert that the shields come back full after a wave that eroded them, and that no saucer is
  up on the first frame of a new wave with a fresh interval rolled.
- **OPEN: Is 1,500 the right extra-life threshold, when a whole wave is worth 990?** It is
  `MISSION.md` §5's own figure and is implemented as written, but the measurement M7 needed
  to test it is the argument against it: six unaided games scored 1210, 1420, 1360, 1330,
  1470 and 30, every one of them short, because a wave holds 990 points of invaders and a
  player has to get well into a second one to reach 1500. That is arguably right — the
  arcade's extra ship was an achievement — but it means the reward for surviving a wave
  arrives in the middle of the next, which is a strange place for it. `EXTRA_LIFE_SCORE` is
  a one-line change; 1000 would put it at the end of a cleared first wave, and 1500 keeps
  it out of reach of anyone who does not clear one. Only playing settles which reads
  better.
- **OPEN: Is 120 frames the right wave pause, and should the banner name the wave that is
  coming?** Two seconds is long enough to read "WAVE 2" and short enough not to be a
  loading screen, but it is reasoned rather than felt, and it is two seconds in which the
  player has nothing to do. The banner names the *next* wave rather than announcing the one
  just cleared, on the grounds that what is useful is what is about to happen;
  `WAVE_CLEAR_FRAMES` and the one string are the tunables.
- **OPEN: Does the wave ramp hold up past wave 3, and are its two floors in the right
  place?** `MISSION.md` §4 requires difficulty to ramp without becoming unwinnable by wave
  3, and wave 3 is measurably gentle: y 32, a step every 45 frames at full fleet, a shell
  every 21. What nothing here can say is where it stops being fair. The march floors at 30
  frames and the gun at 15 — both guesses, unlike the start height, which is derived from
  the shields' position. Reaching wave 6 to find out takes about ten minutes of competent
  play, which is exactly the kind of thing this environment cannot do.
- **OPEN: Is 1 px a frame the right saucer speed?** It is the ship's own speed, which means
  catching the saucer requires leading it by the 51 frames a bullet takes to climb from the
  muzzle to the lane — a skill shot rather than a gift. Measured, not felt: a parked ship
  tapping as fast as the one-shot rule allows hit 7 of 32 crossings, about one in five, which
  is a rate nobody has played. `UFO_SPEED` is a one-line change but an integer-only one in
  both directions — 2 halves both the lead and the crossing, and anything below 1 needs a
  fractional accumulator that nothing else in the file carries.
- **OPEN: Is a flat one-in-four bonus the right feel?** `MISSION.md` §5 lists the four values
  without a rule, so a uniform draw is the literal reading and is what is implemented. The
  arcade's 300 was not random — it was earned on the 23rd shot and every 15th after, a hidden
  rule most players never learned — so a uniform draw means a 300 can only ever be received,
  never earned. Whether that reads as luck or as arbitrary is a question only playing settles.
  `UFO_POINTS` is the tunable; a shot-count rule is the alternative, and it costs a lifetime
  shot counter.
- **OPEN: Is 15 to 25 seconds the right interval, given a wave lasts two to four minutes?**
  It is `MISSION.md` §3's own figure and therefore the best available answer, but it works out
  at five to eight saucers a wave with each crossing only 4.3 s long, so the saucer is in the
  sky roughly a fifth of the time. Whether that is an event or wallpaper is a playing
  question. `UFO_SPAWN_MIN` and `UFO_SPAWN_MAX`, one line each — but see the note above about
  `UFO_FLEET_MIN`: the suppression threshold is the one saucer constant that is not a local
  change.
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
