-- title:  Stauros Invaders
-- author: olavostauros
-- desc:   Space Invaders clone
-- script: lua
-- input:  gamepad
-- saveid: STAUROSINVADERS

-- constants

local SCREEN_W = 240
local SCREEN_H = 136
local FONT_H = 8

local C_BLACK = 0
local C_WHITE = 12

local DEBUG = false

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
}

-- helpers

-- print reports its width only by drawing, so measure with a throwaway pass off-screen.
local function print_centered(text, y, color)
  local w = print(text, 0, -FONT_H, color)
  print(text, math.floor((SCREEN_W - w) / 2), y, color)
end

-- entity update

-- entity draw

-- collision

-- game state machine

-- TIC

function TIC()
  cls(C_BLACK)
  print_centered("HELLO", math.floor((SCREEN_H - FONT_H) / 2), C_WHITE)
end

-- BOOT

function BOOT()
  if DEBUG then
    trace(_VERSION, C_WHITE)
  end
end
