-- appended after game.lua by tools/screendump.py; wraps the cart's own TIC so the
-- pixels dumped are the ones game.lua actually drew.

local PROBE_HOLD = 0
local PROBE_WARMUP = 2
local PROBE_STATE = ""
local PROBE_UFO = 0
local PROBE_LIVES = 0
local PROBE_CLEAR = 0
local PROBE_GAMEPAD = 0x0FF80
-- Button 4 as a gamepad mask. The console reads btnp against a snapshot of the real input
-- device rather than against RAM, so a poked hold registers as a press every frame - which
-- is useless for testing btnp and exactly what is wanted for walking past a title screen.
local PROBE_FIRE_MASK = 16
-- The saucer's own width and the screen's, repeated here because the cart's constants are
-- locals this probe cannot see. Only used to hold the dump until it is wholly on screen.
local PROBE_UFO_W = 16
local PROBE_SCREEN_W = 240

local _TIC = TIC
local probe_frames = 0
local probe_started = false

-- Killing 55 invaders by holding fire takes tens of thousands of frames and the ship is
-- shot down long before, so the shot that ends a wave is forced (LINT-RULES.md L056). The
-- wave banner is the one screen no frame count and no held button can reach.
local function clear_fleet()
  for row = 1, #game.fleet.alive do
    local cells = game.fleet.alive[row]
    for col = 1, #cells do
      cells[col] = false
    end
  end
  game.fleet.count = 0
end

function TIC()
  -- The cart opens on a title screen. Unless that screen is what is being dumped, the
  -- probe presses past it on frames it does not count: a frame number in this tool has
  -- always meant a frame of play. Held fire also leaves a game over, so a dump of that
  -- screen wants --hold 0.
  if not probe_started then
    if game.state == "TITLE" and PROBE_STATE ~= "TITLE" then
      poke(PROBE_GAMEPAD, PROBE_FIRE_MASK)
      _TIC()
      return
    end
    probe_started = true
  end
  poke(PROBE_GAMEPAD, PROBE_HOLD)
  if probe_frames + 1 == PROBE_CLEAR then clear_fleet() end
  -- An idle ship spends its three lives somewhere in the first few thousand frames, and a
  -- game over is a state update_ufo() never runs in, so a dump waiting for the saucer would
  -- wait past the end of the game. Holding the life count keeps it running until one comes.
  if PROBE_LIVES > 0 then game.lives = PROBE_LIVES end
  -- What is on screen during a death or a game over cannot be reached by counting frames:
  -- the console seeds math.random from the clock, so the fleet aims somewhere different
  -- every run and the ship dies on a different frame (docs/lua-notes.md). Waiting for the
  -- state reaches those screens without the probe staging them itself.
  --
  -- Held for the whole frame, not merely true at the end of it: game.lua changes state
  -- after it has drawn, so the frame a death begins on still has the living ship on it -
  -- which is what this dumped before the check read the state on both sides of TIC().
  local entered = game.state
  _TIC()
  probe_frames = probe_frames + 1
  if probe_frames < PROBE_WARMUP then return end
  if PROBE_STATE ~= "" and (entered ~= PROBE_STATE or game.state ~= PROBE_STATE) then
    return
  end
  -- The saucer arrives 15 to 25 seconds in and crosses in four, so no frame number reaches
  -- it - the same reason PROBE_STATE exists. Wholly on screen rather than merely present,
  -- so the pixels dumped are the whole sprite and can be counted against the sheet.
  if PROBE_UFO == 1 and not (game.ufo.active and game.ufo.x >= 0 and
                             game.ufo.x + PROBE_UFO_W <= PROBE_SCREEN_W) then
    return
  end
  trace("VRAMBEGIN", 12)
  for y = 0, 135 do
    local row = {}
    for x = 0, 239 do
      local p = peek4(y * 240 + x)
      row[x + 1] = p == 0 and "." or string.format("%x", p)
    end
    trace(table.concat(row), 12)
  end
  trace("VRAMEND", 12)
  exit()
end
