-- title:  Stauros Invaders
-- author: olavostauros
-- desc:   Space Invaders clone
-- script: lua
-- input:  gamepad
-- saveid: STAUROSINVADERS

-- constants

local SCREEN_W = 240
local SCREEN_H = 136

local C_BLACK = 0
local C_RED = 2
local C_YELLOW = 4
local C_GREEN = 5
local C_WHITE = 12

local BTN_LEFT = 2
local BTN_RIGHT = 3
local BTN_FIRE = 4

local SPRITE_W = 8
local SPRITE_H = 8
local SPR_PLAYER = 0
-- Each invader type occupies two consecutive ids, so the waddle frame is added to the
-- base id rather than looked up.
local SPR_INVADER_TOP = 1
local SPR_INVADER_MID = 3
local SPR_INVADER_LOW = 5
local SPR_PLAYER_EXPLODE = 7
-- The saucer is 16 px wide, so it is one composite spr() of two tiles rather than two
-- calls. The sheet is 16 tiles to a row, so 9 and 10 sit side by side (docs/tic80-ram.md).
local SPR_UFO = 9

-- A tile is 32 bytes of 4-bit pixels and poke4 addresses nibbles, so tile RAM at byte
-- 0x4000 is nibble 0x8000 and each tile spans 64 nibbles in row-major order.
local TILE_NIBBLE_BASE = 0x8000
local TILE_NIBBLES = 64

local PLAYER_SPEED = 1
local PLAYER_Y = 120
local PLAYER_X_MIN = 0
local PLAYER_X_MAX = SCREEN_W - SPRITE_W
local PLAYER_START_X = math.floor((SCREEN_W - SPRITE_W) / 2)
local PLAYER_MUZZLE_X = 3
local PLAYER_LIVES = 3
local PLAYER_DEAD_FRAMES = 90
local PLAYER_EXPLODE_FRAMES = 8

local BULLET_W = 1
local BULLET_H = 3
local BULLET_SPEED = 2

local ENEMY_BULLET_W = 1
local ENEMY_BULLET_H = 3
local ENEMY_BULLET_SPEED = 2
local ENEMY_BULLET_MAX = 3
local ENEMY_FIRE_FRAMES = 25
local ENEMY_MUZZLE_X = 3

local FLEET_COLS = 11
local FLEET_ROWS = 5
local FLEET_COUNT = FLEET_COLS * FLEET_ROWS
local FLEET_COL_SPACING = 16
local FLEET_ROW_SPACING = 10
local FLEET_WIDTH = (FLEET_COLS - 1) * FLEET_COL_SPACING + SPRITE_W
local FLEET_START_X = math.floor((SCREEN_W - FLEET_WIDTH) / 2)
local FLEET_START_Y = 20
local FLEET_STEP_X = 2
local FLEET_DROP_Y = 6
-- The fleet has landed once an invader's bottom edge reaches the ship's top edge, which
-- is a row earlier than the two boxes would overlap: arriving at the player's row is the
-- loss, not touching the player.
local FLEET_LANDING_Y = PLAYER_Y - SPRITE_H
-- The arcade moved one invader per frame, so a full fleet of 55 stepped once every 55
-- frames and the last survivor roughly once every two.
local FLEET_STEP_FRAMES_MAX = 55
local FLEET_STEP_FRAMES_MIN = 2

local FLEET_ROW_SPRITE = {
  SPR_INVADER_TOP,
  SPR_INVADER_MID,
  SPR_INVADER_MID,
  SPR_INVADER_LOW,
  SPR_INVADER_LOW,
}

local FLEET_ROW_POINTS = {
  30,
  20,
  20,
  10,
  10,
}

local BUNKER_COUNT = 4
local BUNKER_COLS = 11
local BUNKER_ROWS = 8
local BUNKER_CELL = 2
local BUNKER_W = BUNKER_COLS * BUNKER_CELL
local BUNKER_H = BUNKER_ROWS * BUNKER_CELL
local BUNKER_PITCH = math.floor(SCREEN_W / BUNKER_COUNT)
local BUNKER_MARGIN = math.floor((BUNKER_PITCH - BUNKER_W) / 2)
-- Low enough to leave clear sky above the ship, high enough that the fleet's bottom row
-- overlaps the band for four drops before landing ends the game.
local BUNKER_Y = 100

local BUNKER_SHAPE = {
  "..#######..",
  ".#########.",
  "###########",
  "###########",
  "###########",
  "###########",
  "####...####",
  "###.....###",
}

-- Offsets cleared around an impact, in cells. Three deep in the bullet's own column, so
-- repeated shots at one spot drill a channel through rather than shaving the face.
local BUNKER_BLAST = {
  { 0, 0 },
  { -1, 0 },
  { 1, 0 },
  { 0, -1 },
  { 0, 1 },
}

-- The lane clears the y 0..7 HUD band the shell draws into and ends 2 px above the fleet's
-- top row, so a bullet under a living invader dies before it can ever reach the saucer.
local UFO_Y = 10
local UFO_TILES = 2
local UFO_W = SPRITE_W * UFO_TILES
-- The ship's own speed, so catching the saucer means leading it by the frames a bullet
-- takes to climb to the lane. Anything slower needs a fractional accumulator, and nothing
-- else in the file carries one.
local UFO_SPEED = 1
local UFO_SPAWN_MIN = 900
local UFO_SPAWN_MAX = 1500
-- The arcade stopped sending the saucer once the wave was nearly cleared, so the last
-- invaders are hunted without a bonus crossing the sky above them.
local UFO_FLEET_MIN = 8

local UFO_POINTS = {
  50,
  100,
  150,
  300,
}

-- Measured in-console 2026-08-18: the default font draws every glyph in a six pixel cell
-- six rows tall, so text is centred by arithmetic rather than by drawing it once off
-- screen to read print()'s width back.
local FONT_W = 6
local FONT_H = 6
local SCORE_FORMAT = "%05d"
local HUD_Y = 0
local HUD_SCORE_X = 2
local HUD_HI_X = 96
local HUD_LIVES_X = 160
local HUD_LIVES_ICON_X = 192
-- The extra life can put a fourth ship on the row, and the band has room for five.
local HUD_LIVES_MAX = 5

local GAME_TITLE = "STAUROS INVADERS"
local BANNER_SCALE = 2
local TITLE_Y = 44
local TITLE_HI_Y = 68
local TITLE_PROMPT_Y = 92
local BANNER_Y = 60
local BANNER_PROMPT_Y = 78
-- Margin cleared around a centred line. The fleet can be anywhere on the screen when a
-- game ends, and white invaders behind red text leave neither readable.
local BANNER_PAD = 2

local EXTRA_LIFE_SCORE = 1500
-- One of pmem's 256 slots. The header's saveid is what keeps it across edits to the cart:
-- without one the console keys saved data on a hash of the script.
local HI_SCORE_SLOT = 0

local WAVE_CLEAR_FRAMES = 120
-- Each wave starts a drop lower than the last, capped so the fleet never starts inside the
-- shields: a wave that opened with its bottom row in the band would crush them on frame 1.
local WAVE_DROP_Y = FLEET_DROP_Y
local FLEET_START_Y_MAX = BUNKER_Y - SPRITE_H - (FLEET_ROWS - 1) * FLEET_ROW_SPACING
-- Both difficulty curves tighten per wave and both have a floor, because a ramp with no
-- bottom is unwinnable by wave five rather than merely hard.
local WAVE_FIRE_STEP = 2
local ENEMY_FIRE_FRAMES_MIN = 15
local WAVE_STEP_TIGHTEN = 5
local FLEET_STEP_FRAMES_FLOOR = 30

-- The cart carries no sprite sheet chunk, so the sheet is drawn here and blitted into
-- tile RAM at boot. A '#' takes the entry's color, anything else stays transparent.
local SPRITE_SHEET = {
  {
    id = SPR_PLAYER,
    color = C_GREEN,
    rows = {
      "...#....",
      "..###...",
      "..###...",
      "#######.",
      "#######.",
      "#######.",
      "#######.",
      "........",
    },
  },
  {
    id = SPR_INVADER_TOP,
    color = C_WHITE,
    rows = {
      "...##...",
      "..####..",
      ".######.",
      "##.##.##",
      "########",
      "..#..#..",
      ".#.##.#.",
      "#.#..#.#",
    },
  },
  {
    id = SPR_INVADER_TOP + 1,
    color = C_WHITE,
    rows = {
      "...##...",
      "..####..",
      ".######.",
      "##.##.##",
      "########",
      ".#.##.#.",
      "#.#..#.#",
      ".#....#.",
    },
  },
  {
    id = SPR_INVADER_MID,
    color = C_WHITE,
    rows = {
      "#......#",
      ".#....#.",
      ".######.",
      "##.##.##",
      "########",
      "#.####.#",
      "#......#",
      ".##..##.",
    },
  },
  {
    id = SPR_INVADER_MID + 1,
    color = C_WHITE,
    rows = {
      "..#..#..",
      "#.####.#",
      ".######.",
      "##.##.##",
      "########",
      "#.####.#",
      ".#....#.",
      "#......#",
    },
  },
  {
    id = SPR_INVADER_LOW,
    color = C_WHITE,
    rows = {
      "..####..",
      ".######.",
      "########",
      "##.##.##",
      "########",
      ".##..##.",
      "#..##..#",
      "#.#..#.#",
    },
  },
  {
    id = SPR_INVADER_LOW + 1,
    color = C_WHITE,
    rows = {
      "..####..",
      ".######.",
      "########",
      "##.##.##",
      "########",
      "..####..",
      ".#.##.#.",
      "#.#..#.#",
    },
  },
  {
    id = SPR_PLAYER_EXPLODE,
    color = C_RED,
    rows = {
      "..#.#...",
      "#..#..#.",
      ".#.###..",
      "#.#####.",
      ".#####.#",
      "#.###.#.",
      "..#.#..#",
      ".#...#..",
    },
  },
  {
    id = SPR_PLAYER_EXPLODE + 1,
    color = C_RED,
    rows = {
      "#..#...#",
      "..#..#..",
      "#.#...#.",
      "...##..#",
      "#..#.#..",
      ".#...#.#",
      "#..#..#.",
      ".#...#..",
    },
  },
  -- The saucer is one 16 x 8 shape split down the middle, so the two halves only read as a
  -- hull and its legs once spr() draws them adjacent.
  {
    id = SPR_UFO,
    color = C_RED,
    rows = {
      ".....###",
      "...#####",
      "..######",
      ".##.##.#",
      "########",
      "..###..#",
      "...##...",
      "........",
    },
  },
  {
    id = SPR_UFO + 1,
    color = C_RED,
    rows = {
      "###.....",
      "#####...",
      "######..",
      "#.##.##.",
      "########",
      "#..###..",
      "...##...",
      "........",
    },
  },
}

-- state

local STATE = {
  TITLE = "TITLE",
  PLAYING = "PLAYING",
  PLAYER_DEAD = "PLAYER_DEAD",
  WAVE_CLEAR = "WAVE_CLEAR",
  GAME_OVER = "GAME_OVER",
}

game = {
  state = STATE.TITLE,
  score = 0,
  -- Read from pmem at boot and written back at game over, so it survives the console
  -- closing; kept live during play because the HUD shows it climbing past the old one.
  hi = 0,
  wave = 1,
  lives = PLAYER_LIVES,
  -- The extra life is once a game, so what is remembered is that it was given rather
  -- than the score it was given at.
  extra_life = false,
  death_timer = 0,
  wave_timer = 0,
  player = { x = PLAYER_START_X, y = PLAYER_Y },
  bullet = { x = 0, y = 0, active = false },
  -- A fixed pool filled in BOOT() rather than a list that grows: the cap on shots in the
  -- air is the number of slots, and nothing allocates while the game is running.
  enemy_bullets = {},
  -- cells is a plain boolean grid indexed [row][col], as fleet.alive is: a table per cell
  -- would buy nothing, and there are 352 of them.
  bunkers = {},
  -- x, y locate row 1 column 1; the fleet is rigid, so every invader's position derives
  -- from that origin. alive is indexed [row][col] and filled in BOOT(); count is what the
  -- step interval reads, so it is kept rather than recounted every frame.
  fleet = {
    x = FLEET_START_X,
    y = FLEET_START_Y,
    dir = 1,
    timer = 0,
    frame = 0,
    fire_timer = 0,
    count = FLEET_COUNT,
    alive = {},
  },
  -- dir doubles as which side the last saucer came from, so the next spawn flips it and
  -- the sides alternate without a second field; starting at -1 sends the first one in from
  -- the left. bonus belongs to the saucer rather than to the shot, so it is rolled when it
  -- enters and read when it dies. The lane never moves, so there is no y for UFO_Y to
  -- drift away from. timer counts down and holds the interval it was rolled with.
  ufo = { x = 0, dir = -1, timer = 0, bonus = 0, active = false },
}

-- helpers

local function clamp(value, low, high)
  if value < low then return low end
  if value > high then return high end
  return value
end

local function blit_sprite_sheet()
  for _, sprite in ipairs(SPRITE_SHEET) do
    local base = TILE_NIBBLE_BASE + sprite.id * TILE_NIBBLES
    for row = 1, SPRITE_H do
      local pixels = sprite.rows[row]
      for col = 1, SPRITE_W do
        local lit = pixels:sub(col, col) == "#"
        poke4(base + (row - 1) * SPRITE_W + (col - 1), lit and sprite.color or C_BLACK)
      end
    end
  end
end

local function build_fleet()
  for row = 1, FLEET_ROWS do
    game.fleet.alive[row] = {}
  end
end

-- The wave curve, in one place. Each is clamped at its own floor rather than at a shared
-- wave number, so the three ramps can be tuned against each other without a cap moving.
local function wave_fleet_y()
  return math.min(FLEET_START_Y + (game.wave - 1) * WAVE_DROP_Y, FLEET_START_Y_MAX)
end

local function wave_fire_frames()
  return math.max(ENEMY_FIRE_FRAMES - (game.wave - 1) * WAVE_FIRE_STEP,
                  ENEMY_FIRE_FRAMES_MIN)
end

local function wave_step_frames_max()
  return math.max(FLEET_STEP_FRAMES_MAX - (game.wave - 1) * WAVE_STEP_TIGHTEN,
                  FLEET_STEP_FRAMES_FLOOR)
end

-- Kept apart from the allocation above for the same reason reset_bunkers() is: a wave
-- restarts inside a frame, and a table constructor there is what L009 forbids.
local function reset_fleet()
  local fleet = game.fleet
  for row = 1, FLEET_ROWS do
    local cells = fleet.alive[row]
    for col = 1, FLEET_COLS do
      cells[col] = true
    end
  end
  fleet.count = FLEET_COUNT
  fleet.x = FLEET_START_X
  fleet.y = wave_fleet_y()
  fleet.dir = 1
  fleet.timer = 0
  fleet.frame = 0
  fleet.fire_timer = 0
end

local function build_bunkers()
  for index = 1, BUNKER_COUNT do
    local cells = {}
    for row = 1, BUNKER_ROWS do
      cells[row] = {}
    end
    game.bunkers[index] = {
      x = BUNKER_MARGIN + (index - 1) * BUNKER_PITCH,
      y = BUNKER_Y,
      cells = cells,
    }
  end
end

-- Kept apart from the allocation above so a wave can restore the shields without a table
-- constructor running inside a frame.
local function reset_bunkers()
  for _, bunker in ipairs(game.bunkers) do
    for row = 1, BUNKER_ROWS do
      local mask = BUNKER_SHAPE[row]
      for col = 1, BUNKER_COLS do
        bunker.cells[row][col] = mask:sub(col, col) == "#"
      end
    end
  end
end

-- Shared by boot and by both ways a saucer can leave, so the interval is the gap between
-- crossings rather than a count from when the last one started: one shot down early does
-- not bring the next one forward.
local function reset_ufo()
  local ufo = game.ufo
  ufo.active = false
  ufo.timer = math.random(UFO_SPAWN_MIN, UFO_SPAWN_MAX)
end

local function build_enemy_bullets()
  for slot = 1, ENEMY_BULLET_MAX do
    game.enemy_bullets[slot] = { x = 0, y = 0, active = false }
  end
end

local function clear_bullets()
  game.bullet.active = false
  for _, bullet in ipairs(game.enemy_bullets) do
    bullet.active = false
  end
end

-- Everything a wave owns, restored together. Called when the transition ends rather than
-- on the frame the last invader died, so the pause draws the field the player left behind
-- and the new wave arrives whole on a single frame.
local function reset_wave()
  reset_fleet()
  reset_bunkers()
  reset_ufo()
  clear_bullets()
  game.player.x = PLAYER_START_X
end

-- Neither of these sets the state: the state machine decides when a fresh game is being
-- played, which is what lets BOOT() build one and leave it sitting behind the title.
local function reset_game()
  game.score = 0
  game.lives = PLAYER_LIVES
  game.wave = 1
  game.extra_life = false
  reset_wave()
end

-- The only writer of game.score. The high score climbs with it rather than at game over,
-- because the HUD shows the two racing; the extra life hangs off the same crossing, and
-- there are two sources of points for it to be missed by.
local function add_score(points)
  game.score = game.score + points
  if game.score > game.hi then game.hi = game.score end
  if not game.extra_life and game.score >= EXTRA_LIFE_SCORE then
    game.extra_life = true
    game.lives = game.lives + 1
  end
end

-- entity update

local function fire()
  local bullet = game.bullet
  if bullet.active then return end
  bullet.x = game.player.x + PLAYER_MUZZLE_X
  bullet.y = PLAYER_Y - BULLET_H
  bullet.active = true
end

local function update_player()
  local player = game.player
  local dx = 0
  if btn(BTN_LEFT) then dx = dx - PLAYER_SPEED end
  if btn(BTN_RIGHT) then dx = dx + PLAYER_SPEED end
  player.x = clamp(player.x + dx, PLAYER_X_MIN, PLAYER_X_MAX)
  -- btnp's hold and period are omitted deliberately: supplying them turns a held
  -- button into auto-fire, and one shot per press is the game's pacing.
  if btnp(BTN_FIRE) then fire() end
end

local function update_bullet()
  local bullet = game.bullet
  if not bullet.active then return end
  bullet.y = bullet.y - BULLET_SPEED
  if bullet.y + BULLET_H <= 0 then bullet.active = false end
end

local function update_enemy_bullets()
  for _, bullet in ipairs(game.enemy_bullets) do
    if bullet.active then
      bullet.y = bullet.y + ENEMY_BULLET_SPEED
      if bullet.y >= SCREEN_H then bullet.active = false end
    end
  end
end

local function bottom_invader(col)
  for row = FLEET_ROWS, 1, -1 do
    if game.fleet.alive[row][col] then return row end
  end
  return nil
end

local function free_enemy_bullet()
  for _, bullet in ipairs(game.enemy_bullets) do
    if not bullet.active then return bullet end
  end
  return nil
end

-- A random column rather than a sweep, and the pick walks forward to the next living one
-- rather than being redrawn: an empty column cannot fire, and rejection sampling has no
-- bound on how long it looks.
local function firing_column()
  local pick = math.random(FLEET_COLS)
  for offset = 0, FLEET_COLS - 1 do
    local col = (pick + offset - 1) % FLEET_COLS + 1
    local row = bottom_invader(col)
    if row then return col, row end
  end
  return nil
end

local function enemy_fire()
  local fleet = game.fleet
  if fleet.count == 0 then return end
  fleet.fire_timer = fleet.fire_timer + 1
  if fleet.fire_timer < wave_fire_frames() then return end
  local bullet = free_enemy_bullet()
  if not bullet then return end
  local col, row = firing_column()
  bullet.x = fleet.x + (col - 1) * FLEET_COL_SPACING + ENEMY_MUZZLE_X
  bullet.y = fleet.y + (row - 1) * FLEET_ROW_SPACING + SPRITE_H
  bullet.active = true
  fleet.fire_timer = 0
end

-- Edges follow the living fleet, not the grid: a column that has been emptied must stop
-- holding the turn back.
local function live_columns()
  local left, right
  for col = 1, FLEET_COLS do
    for row = 1, FLEET_ROWS do
      if game.fleet.alive[row][col] then
        left = left or col
        right = col
        break
      end
    end
  end
  return left, right
end

local function step_fleet()
  local fleet = game.fleet
  fleet.frame = 1 - fleet.frame
  local left, right = live_columns()
  local next_x = fleet.x + fleet.dir * FLEET_STEP_X
  local next_left = next_x + (left - 1) * FLEET_COL_SPACING
  local next_right = next_x + (right - 1) * FLEET_COL_SPACING + SPRITE_W
  if next_left < 0 or next_right > SCREEN_W then
    -- The step that would leave the screen becomes the drop instead of preceding it, so
    -- the fleet always turns flush against the edge.
    fleet.y = fleet.y + FLEET_DROP_Y
    fleet.dir = -fleet.dir
  else
    fleet.x = next_x
  end
end

-- A straight line between the two endpoints. The interval has to fall with the living
-- count rather than with elapsed time, and nothing here can play the game to justify a
-- curvier shape than the one the two endpoints already fix. Later waves lower the top of
-- the line and leave its bottom alone: a wave opens faster, and one invader is one
-- invader whenever it is met.
local function fleet_step_frames()
  local span = wave_step_frames_max() - FLEET_STEP_FRAMES_MIN
  return FLEET_STEP_FRAMES_MIN +
         math.floor((game.fleet.count - 1) * span / (FLEET_COUNT - 1))
end

local function update_fleet()
  local fleet = game.fleet
  -- An emptied fleet has no living columns to bound its step, so it holds where it is.
  if fleet.count == 0 then return end
  fleet.timer = fleet.timer + 1
  if fleet.timer < fleet_step_frames() then return end
  fleet.timer = 0
  step_fleet()
end

-- Entry is a full sprite width outside the screen at both ends, so the saucer slides in
-- and out rather than appearing and vanishing at the edge.
local function spawn_ufo()
  local ufo = game.ufo
  ufo.dir = -ufo.dir
  if ufo.dir > 0 then ufo.x = -UFO_W else ufo.x = SCREEN_W end
  ufo.bonus = UFO_POINTS[math.random(#UFO_POINTS)]
  ufo.active = true
end

local function update_ufo()
  local ufo = game.ufo
  if ufo.active then
    ufo.x = ufo.x + ufo.dir * UFO_SPEED
    if ufo.x >= SCREEN_W or ufo.x + UFO_W <= 0 then reset_ufo() end
    return
  end
  -- The wait does not run down while the fleet is too thin to earn a saucer, so refilling
  -- the sky costs a full interval rather than releasing one that has been counting all
  -- along.
  if game.fleet.count <= UFO_FLEET_MIN then return end
  ufo.timer = ufo.timer - 1
  if ufo.timer <= 0 then spawn_ufo() end
end

-- entity draw

-- Fixed width, so the width of a line is its length times the cell and a centred line
-- needs no measuring pass. It is also what stops the score jittering as its digits change.
local function print_fixed(text, x, y, color, scale)
  print(text, x, y, color, true, scale, false)
end

local function print_centered(text, y, color, scale)
  local width = #text * FONT_W * scale
  local x = math.floor((SCREEN_W - width) / 2)
  rect(x - BANNER_PAD, y - BANNER_PAD, width + BANNER_PAD * 2,
       FONT_H * scale + BANNER_PAD * 2, C_BLACK)
  print_fixed(text, x, y, color, scale)
end

local function score_text(label, value)
  return label .. string.format(SCORE_FORMAT, value)
end

local function draw_hud()
  print_fixed(score_text("SCORE ", game.score), HUD_SCORE_X, HUD_Y, C_WHITE, 1)
  print_fixed(score_text("HI ", game.hi), HUD_HI_X, HUD_Y, C_WHITE, 1)
  print_fixed("LIVES", HUD_LIVES_X, HUD_Y, C_WHITE, 1)
  -- One ship per life, so the count reads without being read: the row is what the player
  -- has left to fly, the ship at the bottom of the screen included.
  local shown = math.min(game.lives, HUD_LIVES_MAX)
  for life = 1, shown do
    spr(SPR_PLAYER, HUD_LIVES_ICON_X + (life - 1) * SPRITE_W, HUD_Y, C_BLACK, 1, 0, 0, 1, 1)
  end
end

local function draw_player()
  spr(SPR_PLAYER, game.player.x, game.player.y, C_BLACK, 1, 0, 0, 1, 1)
end

local function draw_player_explosion()
  local frame = math.floor(game.death_timer / PLAYER_EXPLODE_FRAMES) % 2
  spr(SPR_PLAYER_EXPLODE + frame, game.player.x, game.player.y, C_BLACK, 1, 0, 0, 1, 1)
end

local function draw_bullet()
  local bullet = game.bullet
  if not bullet.active then return end
  rect(bullet.x, bullet.y, BULLET_W, BULLET_H, C_WHITE)
end

-- Enemy shots are yellow against the player's white so the two directions read apart at a
-- glance; both are the same 1 x 3 rect.
local function draw_enemy_bullets()
  for _, bullet in ipairs(game.enemy_bullets) do
    if bullet.active then
      rect(bullet.x, bullet.y, ENEMY_BULLET_W, ENEMY_BULLET_H, C_YELLOW)
    end
  end
end

local function draw_bunkers()
  for _, bunker in ipairs(game.bunkers) do
    for row = 1, BUNKER_ROWS do
      local cells = bunker.cells[row]
      local y = bunker.y + (row - 1) * BUNKER_CELL
      for col = 1, BUNKER_COLS do
        if cells[col] then
          rect(bunker.x + (col - 1) * BUNKER_CELL, y, BUNKER_CELL, BUNKER_CELL, C_GREEN)
        end
      end
    end
  end
end

local function draw_fleet()
  local fleet = game.fleet
  for row = 1, FLEET_ROWS do
    local id = FLEET_ROW_SPRITE[row] + fleet.frame
    local y = fleet.y + (row - 1) * FLEET_ROW_SPACING
    for col = 1, FLEET_COLS do
      if fleet.alive[row][col] then
        spr(id, fleet.x + (col - 1) * FLEET_COL_SPACING, y, C_BLACK, 1, 0, 0, 1, 1)
      end
    end
  end
end

local function draw_ufo()
  local ufo = game.ufo
  if not ufo.active then return end
  spr(SPR_UFO, ufo.x, UFO_Y, C_BLACK, 1, 0, 0, UFO_TILES, 1)
end

-- collision

-- Scanning starts at the edge the shot arrives from, so a rising bullet meets the shield's
-- underside and a falling shell its roof, and each erodes the face it actually touches.
local function bunker_cell(bunker, x, y, w, h, from_below)
  if x >= bunker.x + BUNKER_W or x + w <= bunker.x or
     y >= bunker.y + BUNKER_H or y + h <= bunker.y then
    return nil
  end
  local first, last, step = 1, BUNKER_ROWS, 1
  if from_below then first, last, step = BUNKER_ROWS, 1, -1 end
  for row = first, last, step do
    local cy = bunker.y + (row - 1) * BUNKER_CELL
    if y < cy + BUNKER_CELL and y + h > cy then
      local cells = bunker.cells[row]
      for col = 1, BUNKER_COLS do
        local cx = bunker.x + (col - 1) * BUNKER_CELL
        if cells[col] and x < cx + BUNKER_CELL and x + w > cx then
          return col, row
        end
      end
    end
  end
  return nil
end

local function erode_bunker(bunker, col, row)
  for _, offset in ipairs(BUNKER_BLAST) do
    local c, r = col + offset[1], row + offset[2]
    if c >= 1 and c <= BUNKER_COLS and r >= 1 and r <= BUNKER_ROWS then
      bunker.cells[r][c] = false
    end
  end
end

local function collide_bullet_bunkers()
  local bullet = game.bullet
  if not bullet.active then return end
  for _, bunker in ipairs(game.bunkers) do
    local col, row = bunker_cell(bunker, bullet.x, bullet.y, BULLET_W, BULLET_H, true)
    if col then
      erode_bunker(bunker, col, row)
      bullet.active = false
      return
    end
  end
end

local function collide_enemy_bullets_bunkers()
  for _, bullet in ipairs(game.enemy_bullets) do
    if bullet.active then
      for _, bunker in ipairs(game.bunkers) do
        local col, row = bunker_cell(bunker, bullet.x, bullet.y,
                                     ENEMY_BULLET_W, ENEMY_BULLET_H, false)
        if col then
          erode_bunker(bunker, col, row)
          bullet.active = false
          break
        end
      end
    end
  end
end

local function crush_bunker(bunker, x, y)
  if x >= bunker.x + BUNKER_W or x + SPRITE_W <= bunker.x then return end
  for row = 1, BUNKER_ROWS do
    local cy = bunker.y + (row - 1) * BUNKER_CELL
    if y < cy + BUNKER_CELL and y + SPRITE_H > cy then
      local cells = bunker.cells[row]
      for col = 1, BUNKER_COLS do
        local cx = bunker.x + (col - 1) * BUNKER_CELL
        if x < cx + BUNKER_CELL and x + SPRITE_W > cx then cells[col] = false end
      end
    end
  end
end

-- An invader standing in a shield erases it outright rather than eroding it. Bounded by a
-- single compare until the fleet has descended far enough to reach the band at all.
local function crush_bunkers()
  local fleet = game.fleet
  if fleet.y + (FLEET_ROWS - 1) * FLEET_ROW_SPACING + SPRITE_H <= BUNKER_Y then return end
  for row = 1, FLEET_ROWS do
    local y = fleet.y + (row - 1) * FLEET_ROW_SPACING
    if y < BUNKER_Y + BUNKER_H and y + SPRITE_H > BUNKER_Y then
      for col = 1, FLEET_COLS do
        if fleet.alive[row][col] then
          local x = fleet.x + (col - 1) * FLEET_COL_SPACING
          for _, bunker in ipairs(game.bunkers) do
            crush_bunker(bunker, x, y)
          end
        end
      end
    end
  end
end

local function invader_hit(row, col)
  local fleet = game.fleet
  local bullet = game.bullet
  local x = fleet.x + (col - 1) * FLEET_COL_SPACING
  local y = fleet.y + (row - 1) * FLEET_ROW_SPACING
  return bullet.x < x + SPRITE_W and bullet.x + BULLET_W > x and
         bullet.y < y + SPRITE_H and bullet.y + BULLET_H > y
end

-- The order of the scan does not matter: a 1 x 3 bullet cannot span two invaders at a
-- 16 px column pitch or a 10 px row pitch, so at most one cell can match.
local function collide_bullet_fleet()
  local bullet = game.bullet
  if not bullet.active then return end
  local fleet = game.fleet
  for row = 1, FLEET_ROWS do
    for col = 1, FLEET_COLS do
      if fleet.alive[row][col] and invader_hit(row, col) then
        fleet.alive[row][col] = false
        fleet.count = fleet.count - 1
        add_score(FLEET_ROW_POINTS[row])
        bullet.active = false
        return
      end
    end
  end
end

-- The lane and the fleet's rows are disjoint bands, so this cannot steal a kill from
-- collide_bullet_fleet(); it runs after it because that is the order a rising bullet meets
-- them.
local function collide_bullet_ufo()
  local ufo = game.ufo
  local bullet = game.bullet
  if not ufo.active or not bullet.active then return end
  if bullet.x < ufo.x + UFO_W and bullet.x + BULLET_W > ufo.x and
     bullet.y < UFO_Y + SPRITE_H and bullet.y + BULLET_H > UFO_Y then
    add_score(ufo.bonus)
    bullet.active = false
    reset_ufo()
  end
end

local function player_hit()
  local player = game.player
  for _, bullet in ipairs(game.enemy_bullets) do
    if bullet.active and
       bullet.x < player.x + SPRITE_W and bullet.x + ENEMY_BULLET_W > player.x and
       bullet.y < player.y + SPRITE_H and bullet.y + ENEMY_BULLET_H > player.y then
      bullet.active = false
      return true
    end
  end
  return false
end

-- The lowest living row, not row 5: a bottom row that has been shot away must not keep the
-- fleet aloft.
local function fleet_landed()
  local fleet = game.fleet
  for row = FLEET_ROWS, 1, -1 do
    for col = 1, FLEET_COLS do
      if fleet.alive[row][col] then
        return fleet.y + (row - 1) * FLEET_ROW_SPACING >= FLEET_LANDING_Y
      end
    end
  end
  return false
end

-- game state machine

-- pmem is written once a game rather than once a point: the slot outlives the console
-- being closed, and nothing can change the score after the last life is spent.
local function end_game()
  game.state = STATE.GAME_OVER
  pmem(HI_SCORE_SLOT, game.hi)
end

local function kill_player()
  game.lives = game.lives - 1
  game.death_timer = PLAYER_DEAD_FRAMES
  game.state = STATE.PLAYER_DEAD
  -- Shells already in the air would otherwise be waiting on the respawned ship, and the
  -- player's own shot belongs to the life that just ended.
  clear_bullets()
  game.fleet.fire_timer = 0
end

local function state_playing()
  update_player()
  update_bullet()
  update_enemy_bullets()
  update_fleet()
  enemy_fire()
  update_ufo()
  -- The shields are read before the fleet: an invader low enough to share a pixel with a
  -- bunker cell has already crushed it, so this never steals a kill.
  collide_bullet_bunkers()
  collide_bullet_fleet()
  collide_bullet_ufo()
  collide_enemy_bullets_bunkers()
  crush_bunkers()
  draw_player()
  draw_bunkers()
  draw_bullet()
  draw_enemy_bullets()
  draw_fleet()
  draw_ufo()
  draw_hud()
  -- Landing is read first so it wins on a frame that is also a hit: it ends the game
  -- whatever the life count says. The wave is read last for the mirror of that reason: a
  -- shell already falling when the last invader died still takes the life it was aimed at,
  -- and the empty fleet is still empty on the other side of the pause.
  if fleet_landed() then
    end_game()
  elseif player_hit() then
    kill_player()
  elseif game.fleet.count == 0 then
    game.state = STATE.WAVE_CLEAR
    game.wave_timer = WAVE_CLEAR_FRAMES
  end
end

local function state_player_dead()
  game.death_timer = game.death_timer - 1
  if game.death_timer <= 0 then
    if game.lives > 0 then
      game.player.x = PLAYER_START_X
      game.state = STATE.PLAYING
    else
      end_game()
    end
  end
  draw_player_explosion()
  draw_bunkers()
  draw_fleet()
  draw_ufo()
  draw_hud()
end

-- No entity is drawn or updated here, which is also how the saucer is kept off the title
-- screen: the freeze is the absence of an update call rather than a flag.
local function state_title()
  print_centered(GAME_TITLE, TITLE_Y, C_GREEN, BANNER_SCALE)
  print_centered(score_text("HI ", game.hi), TITLE_HI_Y, C_WHITE, 1)
  print_centered("PRESS A", TITLE_PROMPT_Y, C_YELLOW, 1)
  if btnp(BTN_FIRE) then
    reset_game()
    game.state = STATE.PLAYING
  end
end

-- The field the wave was won on, held still: the shields still eroded, the ship still
-- where it was standing, and the banner naming the wave that is coming rather than the one
-- that just ended. reset_wave() restores all of it on the frame the pause runs out, which
-- is also what keeps a saucer off the transition - it is not drawn here, and the one that
-- was crossing is gone before the next wave's first frame.
local function state_wave_clear()
  draw_player()
  draw_bunkers()
  draw_hud()
  print_centered("WAVE " .. (game.wave + 1), BANNER_Y, C_WHITE, BANNER_SCALE)
  game.wave_timer = game.wave_timer - 1
  if game.wave_timer <= 0 then
    game.wave = game.wave + 1
    reset_wave()
    game.state = STATE.PLAYING
  end
end

local function state_game_over()
  -- A ship is still standing only when the fleet landed on it; running out of lives left
  -- nothing to draw.
  if game.lives > 0 then draw_player() end
  draw_bunkers()
  draw_enemy_bullets()
  draw_fleet()
  draw_ufo()
  draw_hud()
  print_centered("GAME OVER", BANNER_Y, C_RED, BANNER_SCALE)
  print_centered("PRESS A", BANNER_PROMPT_Y, C_YELLOW, 1)
  -- Back to the title rather than straight into a game, so the score stays on screen until
  -- someone chooses to leave it.
  if btnp(BTN_FIRE) then game.state = STATE.TITLE end
end

local STATE_FRAME = {
  [STATE.TITLE] = state_title,
  [STATE.PLAYING] = state_playing,
  [STATE.PLAYER_DEAD] = state_player_dead,
  [STATE.WAVE_CLEAR] = state_wave_clear,
  [STATE.GAME_OVER] = state_game_over,
}

-- TIC

function TIC()
  cls(C_BLACK)
  STATE_FRAME[game.state]()
end

-- BOOT

function BOOT()
  blit_sprite_sheet()
  build_fleet()
  build_enemy_bullets()
  build_bunkers()
  game.hi = pmem(HI_SCORE_SLOT)
  reset_game()
end
