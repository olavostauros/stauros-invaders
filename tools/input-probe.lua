-- appended after game.lua by tools/inputsim.py; wraps the cart's own TIC so the code
-- under test runs unmodified, drives the gamepad, and reports game state per frame.

local PROBE_SCRIPT = {}
local PROBE_CLEAR = 0
local PROBE_FLEET = {}
local PROBE_LIVES = 0
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

-- Marching the fleet down to the player's row takes about thirty thousand frames and the
-- ship would be shot down long before, so the landing is reached by placing the fleet one
-- drop above it. Stands in for two minutes of the fleet marching.
local function place_fleet()
  game.fleet.x = PROBE_FLEET[2]
  game.fleet.y = PROBE_FLEET[3]
end

-- One bit per column rather than a count, so a shot can be checked against the bottom-most
-- living invader of its column and not merely against how many are left in the row.
local function row_masks()
  local out = ""
  for row = 1, #game.fleet.alive do
    local mask = 0
    for col, alive in ipairs(game.fleet.alive[row]) do
      if alive then mask = mask | (1 << (col - 1)) end
    end
    out = out .. " " .. mask
  end
  return out
end

-- Liveness is its own field per slot; a spent slot keeps its last coordinates and they are
-- not to be read.
local function enemy_bullets()
  local out = ""
  for _, bullet in ipairs(game.enemy_bullets) do
    out = out .. " " .. (bullet.active and 1 or 0) .. " " .. bullet.x .. " " .. bullet.y
  end
  return out
end

-- One 11-bit mask per bunker row, bunker-major. A live-cell count would answer "how much
-- is left" but not "which side did it go from", and erosion direction is half of what M5
-- has to show.
local function bunker_masks()
  local out = ""
  for _, bunker in ipairs(game.bunkers) do
    for row = 1, #bunker.cells do
      local mask = 0
      for col, alive in ipairs(bunker.cells[row]) do
        if alive then mask = mask | (1 << (col - 1)) end
      end
      out = out .. " " .. mask
    end
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
  if frame == PROBE_FLEET[1] then place_fleet() end
  -- A fixed script cannot dodge a shell aimed at a column it did not know would fire, so a
  -- scenario that has to outlive the fleet rather than the threat keeps its lives topped up.
  -- Death, the explosion and the respawn all still run; only the game over never arrives.
  if PROBE_LIVES > 0 then game.lives = PROBE_LIVES end
  _TIC()
  -- the bullet's y goes negative before it despawns, so liveness is its own field
  -- rather than a sentinel coordinate.
  trace("[" .. frame .. " " .. mask .. " " .. game.player.x .. " " ..
        (game.bullet.active and 1 or 0) .. " " ..
        game.bullet.y .. " " .. game.bullet.x .. " " .. console_btnp .. " " ..
        game.fleet.x .. " " .. game.fleet.y .. " " .. game.fleet.dir .. " " ..
        game.fleet.frame .. " " .. game.score .. row_masks() .. " " ..
        game.state .. " " .. game.lives .. " " .. game.death_timer ..
        enemy_bullets() .. bunker_masks() .. "]", 12)
end
