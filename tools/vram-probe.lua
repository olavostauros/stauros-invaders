-- appended after game.lua by scratch/screendump.sh; wraps the cart's own TIC so the
-- pixels dumped are the ones game.lua actually drew.

local _TIC = TIC
local probe_frames = 0

function TIC()
  _TIC()
  probe_frames = probe_frames + 1
  if probe_frames < 2 then return end
  trace("VRAMBEGIN", 12)
  for y = 0, 135 do
    local row = {}
    for x = 0, 239 do
      local p = peek4(y * 240 + x)
      row[x + 1] = p == 0 and "." or string.format("%x", p)
    end
    trace(table.concat(row), 12)
  end
  trace("VRAMEND", 12)
  exit()
end
