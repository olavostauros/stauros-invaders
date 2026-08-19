-- appended after game.lua by tools/inputsim.py; wraps the cart's own TIC so the code
-- under test runs unmodified, drives the gamepad, and reports game state per frame.
--
-- Everything below is scoped inside one function: a probe is concatenated onto game.lua
-- and shares its main chunk, where Lua allows 200 locals in total (LINT-RULES.md L063).
-- Left at the top level these would be counted against the cart's own.
local function probe()
  local PROBE_SCRIPT = {}
  local PROBE_REPEAT = 1
  local PROBE_CLEAR = 0
  local PROBE_FLEET = {}
  local PROBE_LIVES = 0
  local PROBE_KEEP = 0
  local PROBE_RUSH = 0
  local PROBE_ENDLESS = 0
  local PROBE_TITLE = 0
  local PROBE_HI = -1
  local PROBE_GAMEPAD = 0x0FF80
  local PROBE_REGISTERS = 0x0FF9C
  local PROBE_CHANNELS = 4
  local PROBE_REGISTER_BYTES = 18
  local PROBE_HI_SLOT = 0
  local PROBE_FIRE = 4

  local _TIC = TIC
  local _btnp = btnp
  local frame = 0
  local mask = 0
  local prev_mask = 0
  local console_btnp = 0
  local started = false

  -- A saved high score is the one piece of state no script can reach: it is left behind by
  -- a game played before this console was launched. Written here rather than into game.hi
  -- because what is being tested is that the cart reads the slot, and this file runs before
  -- BOOT() does.
  if PROBE_HI >= 0 then pmem(PROBE_HI_SLOT, PROBE_HI) end

  -- The console's btnp compares the gamepad against a snapshot taken from the real input
  -- device, not from RAM, so a poked hold reads as a fresh press every frame. Edge-detect
  -- against the mask this probe wrote, which is what a human holding the button produces.
  function btnp(id, hold, period)
    local bit = 1 << id
    return (mask & bit) ~= 0 and (prev_mask & bit) == 0
  end

  -- Clearing the fleet through the gamepad would take tens of thousands of frames and land
  -- on a fleet position nothing can reproduce, so the empty-fleet guard is reached by
  -- forcing the state instead. Stands in for the last kill of a wave, or with PROBE_KEEP
  -- above zero for the shots that thin one down to its last few. Survivors are taken from
  -- the top row: a fleet of eight steps every eight frames and a bottom-row remnant would
  -- walk itself onto the player's row before a long scenario finished.
  local function clear_fleet()
    local left = PROBE_KEEP
    for row = 1, #game.fleet.alive do
      local cells = game.fleet.alive[row]
      for col = 1, #cells do
        cells[col] = left > 0
        if left > 0 then left = left - 1 end
      end
    end
    game.fleet.count = PROBE_KEEP - left
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

  -- The sound registers are the only readable trace of what the cart is playing: nothing in
  -- this environment can hear the console, and the SFX bank says what a sound would be, not
  -- whether one is sounding. Each channel holds a 12-bit frequency, then a 4-bit volume,
  -- then the waveform the sample was copied into; peek4 addresses nibbles, so the byte
  -- address doubles. Volume is zero on a silent channel, which is what "no sound" reads as.
  local function channels()
    local out = ""
    for channel = 0, PROBE_CHANNELS - 1 do
      local a = (PROBE_REGISTERS + channel * PROBE_REGISTER_BYTES) * 2
      out = out .. " " .. (peek4(a) + peek4(a + 1) * 16 + peek4(a + 2) * 256) ..
            " " .. peek4(a + 3)
    end
    return out
  end

  -- timer is the liveness, so a spent slot's coordinates and its last bonus are traced but
  -- not to be read.
  local function explosions()
    local out = ""
    for _, burst in ipairs(game.explosions) do
      out = out .. " " .. burst.timer .. " " .. burst.x .. " " .. burst.y ..
            " " .. burst.bonus
    end
    return out
  end

  -- The script is one cycle and a count of how many times it runs, rather than a segment
  -- per frame: a scenario that alternates left and right for 2,800 frames is two segments
  -- here, not 2,800. The cart has room for game.lua, this probe and the table between them,
  -- and the table is the part that grows without limit (LINT-RULES.md L064). It also stops
  -- the walk below being a scan of the whole script on every frame of it.
  local PROBE_CYCLE = 0
  for _, segment in ipairs(PROBE_SCRIPT) do
    PROBE_CYCLE = PROBE_CYCLE + segment[1]
  end

  local function mask_at(f)
    if f > PROBE_CYCLE * PROBE_REPEAT then return nil end
    local at = (f - 1) % PROBE_CYCLE + 1
    local last = 0
    for _, segment in ipairs(PROBE_SCRIPT) do
      last = last + segment[1]
      if at <= last then return segment[2] end
    end
    return nil
  end

  function TIC()
    -- The game opens on a title screen now, and a script cannot spend a frame on the press
    -- that leaves it without shifting every frame number in every scenario written before
    -- M7. The probe presses A itself, through its own btnp, on frames it does not count:
    -- frame 1 of a script is still the first frame of a game. The mask is dropped again
    -- afterwards, so a script that fires on frame 1 still gets a fresh press.
    if not started then
      -- A scenario about the title screen has to be traced on it, so the press is left to
      -- the script and frame 1 is the first frame of the title rather than of play.
      if PROBE_TITLE == 1 then
        started = true
      elseif game.state == "TITLE" then
        prev_mask, mask = 0, 1 << PROBE_FIRE
        poke(PROBE_GAMEPAD, mask)
        _TIC()
        mask, prev_mask = 0, 0
        return
      end
      started = true
    end
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
    --
    -- A top-up rather than an assignment: the extra life is a life the game gives, and one
    -- set every frame would take it straight back. Nothing could add a life before M7, so
    -- this is the same forcing every earlier scenario ran under.
    if PROBE_LIVES > 0 and game.lives < PROBE_LIVES then game.lives = PROBE_LIVES end
    -- Watching eight saucers cross at the real interval is four minutes of play. The wait
    -- between them is compressed here and nothing else is: the crossing, the side, the bonus
    -- and the collision all stay the game's own. Stands in for the minutes a player spends
    -- between saucers.
    --
    -- Clamped before the cart runs, not after, so the interval the cart rolled is still the
    -- one traced on the frame it was rolled. Clamping afterwards would overwrite every roll
    -- with PROBE_RUSH and leave nothing to check the 15-to-25-second band against.
    if PROBE_RUSH > 0 and game.ufo.timer > PROBE_RUSH then
      game.ufo.timer = PROBE_RUSH
    end
    _TIC()
    -- An empty sky is no longer a state the game can be left in: the wave ends and the next
    -- one arrives. The scenarios whose subject predates waves - movement, the single bullet,
    -- the empty-fleet guard - clear the fleet only to get it out of the way, and they hold
    -- the transition off to keep it out. This stands in for no player action at all, so it
    -- is never used by a scenario about waves. Entering WAVE_CLEAR sets the state and the
    -- timer and nothing else, which is why putting the state back is the whole of it.
    if PROBE_ENDLESS == 1 and game.state == "WAVE_CLEAR" then
      game.state = "PLAYING"
    end
    -- the bullet's y goes negative before it despawns, so liveness is its own field
    -- rather than a sentinel coordinate. The saucer's x is off screen at both ends of every
    -- crossing for the same reason. Its bonus is traced rather than only the score: a saucer
    -- nobody shoots still carries a value, and that value is what shows the roll happened
    -- when it entered rather than when it was hit.
    trace("[" .. frame .. " " .. mask .. " " .. game.player.x .. " " ..
          (game.bullet.active and 1 or 0) .. " " ..
          game.bullet.y .. " " .. game.bullet.x .. " " .. console_btnp .. " " ..
          game.fleet.x .. " " .. game.fleet.y .. " " .. game.fleet.dir .. " " ..
          game.fleet.frame .. " " .. game.score .. row_masks() .. " " ..
          game.state .. " " .. game.lives .. " " .. game.death_timer ..
          enemy_bullets() .. bunker_masks() .. " " ..
          (game.ufo.active and 1 or 0) .. " " .. game.ufo.x .. " " .. game.ufo.dir ..
          " " .. game.ufo.bonus .. " " .. game.ufo.timer .. " " ..
          game.wave .. " " .. game.hi .. " " .. game.wave_timer .. " " ..
          (game.extra_life and 1 or 0) .. explosions() .. channels() .. "]", 12)
  end
end

probe()
