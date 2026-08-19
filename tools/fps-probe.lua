-- appended after game.lua by tools/fpscheck.py. Measures the console's actual frame
-- pacing over a fixed number of frames, using time() rather than a host-side stopwatch
-- so window startup and shutdown are excluded from the sample.
--
-- Scoped inside one function for the reason tools/input-probe.lua gives: a probe shares
-- game.lua's main chunk and its 200-local budget (LINT-RULES.md L063).
local function probe()
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
  local PROBE_REGISTERS = 0x0FF9C
  local PROBE_CHANNELS = 4
  local PROBE_REGISTER_BYTES = 18

  local probe_started = false
  -- The load over the whole sample rather than on its last frame: the saucer crosses for
  -- four seconds of a twenty-second window and a burst is gone in twelve frames, so a
  -- snapshot at the end reports an empty screen for a window that was full.
  local probe_saucer = 0
  local probe_bursts = 0
  local probe_voices = 0
  local probe_sounding = 0

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
    if game.ufo.active then probe_saucer = probe_saucer + 1 end
    local bursts = 0
    for _, burst in ipairs(game.explosions) do
      if burst.timer > 0 then bursts = bursts + 1 end
    end
    if bursts > probe_bursts then probe_bursts = bursts end
    local voices = 0
    for channel = 0, PROBE_CHANNELS - 1 do
      local a = (PROBE_REGISTERS + channel * PROBE_REGISTER_BYTES) * 2
      if peek4(a + 3) > 0 then voices = voices + 1 end
    end
    if voices > probe_voices then probe_voices = voices end
    if voices > 0 then probe_sounding = probe_sounding + 1 end
    if probe_frames == PROBE_WARMUP then
      probe_t0 = time()
    elseif probe_frames == PROBE_WARMUP + PROBE_SAMPLE then
      -- What was actually on screen and in the speakers, so the number above can be read
      -- against the load it was measured under rather than against a claim about it: a
      -- sample whose ship is long dead measures a still picture.
      trace("LOAD state " .. game.state .. " invaders " .. game.fleet.count ..
            " saucerframes " .. probe_saucer .. " peakbursts " .. probe_bursts ..
            " peakvoices " .. probe_voices .. " soundingframes " .. probe_sounding, 12)
      local ms = time() - probe_t0
      trace("FPS " .. string.format("%.3f", PROBE_SAMPLE * 1000 / ms)
        .. " over " .. PROBE_SAMPLE .. " frames in " .. string.format("%.1f", ms) .. " ms", 12)
      exit()
    end
  end
end

probe()
