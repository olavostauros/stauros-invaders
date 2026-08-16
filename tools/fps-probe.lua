-- appended after game.lua by scratch/fpscheck.sh. Measures the console's actual frame
-- pacing over a fixed number of frames, using time() rather than a host-side stopwatch
-- so window startup and shutdown are excluded from the sample.

local _TIC = TIC
local probe_frames = 0
local probe_t0 = 0
local PROBE_SAMPLE = 600
local PROBE_WARMUP = 60

function TIC()
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
