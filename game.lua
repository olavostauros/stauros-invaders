-- title:  Stauros Invaders
-- author: olavostauros
-- desc:   Space Invaders clone
-- script: lua
-- input:  gamepad
-- saveid: STAUROSINVADERS

-- constants

local SCREEN_W = 240

local C_BLACK = 0
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

local BULLET_W = 1
local BULLET_H = 3
local BULLET_SPEED = 2

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
  state = STATE.PLAYING,
  score = 0,
  player = { x = PLAYER_START_X, y = PLAYER_Y },
  bullet = { x = 0, y = 0, active = false },
  -- x, y locate row 1 column 1; the fleet is rigid, so every invader's position derives
  -- from that origin. alive is indexed [row][col] and filled in BOOT(); count is what the
  -- step interval reads, so it is kept rather than recounted every frame.
  fleet = {
    x = FLEET_START_X,
    y = FLEET_START_Y,
    dir = 1,
    timer = 0,
    frame = 0,
    count = FLEET_COUNT,
    alive = {},
  },
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
    local cells = {}
    for col = 1, FLEET_COLS do
      cells[col] = true
    end
    game.fleet.alive[row] = cells
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
-- curvier shape than the one the two endpoints already fix.
local function fleet_step_frames()
  local span = FLEET_STEP_FRAMES_MAX - FLEET_STEP_FRAMES_MIN
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

-- entity draw

local function draw_player()
  spr(SPR_PLAYER, game.player.x, game.player.y, C_BLACK, 1, 0, 0, 1, 1)
end

local function draw_bullet()
  local bullet = game.bullet
  if not bullet.active then return end
  rect(bullet.x, bullet.y, BULLET_W, BULLET_H, C_WHITE)
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

-- collision

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
        game.score = game.score + FLEET_ROW_POINTS[row]
        bullet.active = false
        return
      end
    end
  end
end

-- TIC

function TIC()
  cls(C_BLACK)
  update_player()
  update_bullet()
  update_fleet()
  collide_bullet_fleet()
  draw_player()
  draw_bullet()
  draw_fleet()
end

-- BOOT

function BOOT()
  blit_sprite_sheet()
  build_fleet()
end
