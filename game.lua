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
  player = { x = PLAYER_START_X, y = PLAYER_Y },
  bullet = { x = 0, y = 0, active = false },
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

-- entity draw

local function draw_player()
  spr(SPR_PLAYER, game.player.x, game.player.y, C_BLACK, 1, 0, 0, 1, 1)
end

local function draw_bullet()
  local bullet = game.bullet
  if not bullet.active then return end
  rect(bullet.x, bullet.y, BULLET_W, BULLET_H, C_WHITE)
end

-- TIC

function TIC()
  cls(C_BLACK)
  update_player()
  update_bullet()
  draw_player()
  draw_bullet()
end

-- BOOT

function BOOT()
  blit_sprite_sheet()
end
