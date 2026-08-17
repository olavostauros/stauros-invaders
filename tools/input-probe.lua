-- appended after game.lua by tools/inputsim.py; wraps the cart's own TIC so the code
-- under test runs unmodified, drives the gamepad, and reports game state per frame.

local PROBE_SCRIPT = {}
local PROBE_CLEAR = 0
local PROBE_GAMEPAD = 0x0FF80
local PROBE_FIRE = 4

local _TIC = TIC
local _btnp = btnp
local frame = 0
local mask = 0
local prev_mask = 0
local console_btnp = 0

-- The console's btnp compares the gamepad against a snapshot taken from the real input
-- device, not from RAM, so a poked hold reads as a fresh press every frame. Edge-detect
-- against the mask this probe wrote, which is what a human holding the button produces.
function btnp(id, hold, period)
  local bit = 1 << id
  return (mask & bit) ~= 0 and (prev_mask & bit) == 0
end

-- Clearing the fleet through the gamepad would take tens of thousands of frames and land
-- on a fleet position nothing can reproduce, so the empty-fleet guard is reached by
-- forcing the state instead. Stands in for the last kill of a wave.
local function clear_fleet()
  for row = 1, #game.fleet.alive do
    local cells = game.fleet.alive[row]
    for col = 1, #cells do
      cells[col] = false
    end
  end
  game.fleet.count = 0
end

-- Per-row counts rather than one total, so a kill can be attributed to the row whose
-- point value the score is supposed to have gone up by.
local function row_counts()
  local out = ""
  for row = 1, #game.fleet.alive do
    local n = 0
    for _, alive in ipairs(game.fleet.alive[row]) do
      if alive then n = n + 1 end
    end
    out = out .. " " .. n
  end
  return out
end

local function mask_at(f)
  local last = 0
  for _, segment in ipairs(PROBE_SCRIPT) do
    last = last + segment[1]
    if f <= last then return segment[2] end
  end
  return nil
end

function TIC()
  frame = frame + 1
  local next_mask = mask_at(frame)
  if next_mask == nil then
    trace("[PROBEEND]", 12)
    exit()
    return
  end
  prev_mask = mask
  mask = next_mask
  poke(PROBE_GAMEPAD, mask)
  -- reported so a console that ever starts honouring RAM writes here gets noticed and
  -- the btnp substitution above can be retired.
  console_btnp = _btnp(PROBE_FIRE) and 1 or 0
  if frame == PROBE_CLEAR then clear_fleet() end
  _TIC()
  -- the bullet's y goes negative before it despawns, so liveness is its own field
  -- rather than a sentinel coordinate.
  trace("[" .. frame .. " " .. mask .. " " .. game.player.x .. " " ..
        (game.bullet.active and 1 or 0) .. " " ..
        game.bullet.y .. " " .. game.bullet.x .. " " .. console_btnp .. " " ..
        game.fleet.x .. " " .. game.fleet.y .. " " .. game.fleet.dir .. " " ..
        game.fleet.frame .. " " .. game.score .. row_counts() .. "]", 12)
end
