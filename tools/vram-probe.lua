-- appended after game.lua by tools/screendump.py; wraps the cart's own TIC so the
-- pixels dumped are the ones game.lua actually drew.

local PROBE_HOLD = 0
local PROBE_WARMUP = 2
local PROBE_STATE = ""
local PROBE_GAMEPAD = 0x0FF80

local _TIC = TIC
local probe_frames = 0

function TIC()
  poke(PROBE_GAMEPAD, PROBE_HOLD)
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
