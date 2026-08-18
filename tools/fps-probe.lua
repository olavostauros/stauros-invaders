-- appended after game.lua by tools/fpscheck.py. Measures the console's actual frame
-- pacing over a fixed number of frames, using time() rather than a host-side stopwatch
-- so window startup and shutdown are excluded from the sample.

local _TIC = TIC
local probe_frames = 0
local probe_t0 = 0
local PROBE_SAMPLE = 600
local PROBE_WARMUP = 60
local PROBE_HOLD = 0
local PROBE_GAMEPAD = 0x0FF80
-- Button 4 as a gamepad mask, for walking past the title screen: the console reads btnp
-- against the real input device rather than against RAM, so a poked hold is a press every
-- frame. The frames it takes are not sampled - the measurement is of play.
local PROBE_FIRE_MASK = 16

local probe_started = false

function TIC()
  if not probe_started then
    if game.state == "TITLE" then
      poke(PROBE_GAMEPAD, PROBE_FIRE_MASK)
      _TIC()
      return
    end
    probe_started = true
  end
  poke(PROBE_GAMEPAD, PROBE_HOLD)
  _TIC()
  probe_frames = probe_frames + 1
  if probe_frames == PROBE_WARMUP then
    probe_t0 = time()
  elseif probe_frames == PROBE_WARMUP + PROBE_SAMPLE then
    local ms = time() - probe_t0
    trace("FPS " .. string.format("%.3f", PROBE_SAMPLE * 1000 / ms)
      .. " over " .. PROBE_SAMPLE .. " frames in " .. string.format("%.1f", ms) .. " ms", 12)
    exit()
  end
end
