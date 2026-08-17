-- appended after game.lua by tools/inputsim.py; wraps the cart's own TIC so the code
-- under test runs unmodified, drives the gamepad, and reports game state per frame.

local PROBE_SCRIPT = {}
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
  _TIC()
  -- the bullet's y goes negative before it despawns, so liveness is its own field
  -- rather than a sentinel coordinate.
  trace("[" .. frame .. " " .. mask .. " " .. game.player.x .. " " ..
        (game.bullet.active and 1 or 0) .. " " ..
        game.bullet.y .. " " .. game.bullet.x .. " " .. console_btnp .. " " ..
        game.fleet.x .. " " .. game.fleet.y .. " " .. game.fleet.dir .. " " ..
        game.fleet.frame .. "]", 12)
end
