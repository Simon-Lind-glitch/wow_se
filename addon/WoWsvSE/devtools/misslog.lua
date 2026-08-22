-- Development-only miss logger.
--
-- Records origin-tagged strings that rendered without a translation, so the
-- gaps for the next build can be read out of SavedVariables between sessions.
--
-- This is a build tool, not a feature (spec §7). Off unless the debug flag is
-- set, and it has no UI, no messages and nothing the kids will ever see. The
-- only visible effect of leaving it off is that WoWsvSE.lua stays small.

local _, SVSE = ...

local MAX_ENTRIES = 2000

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function()
  local db = SVSE.Settings()
  if not db.debug then
    return
  end

  local misses = db.misses
  local count = 0
  for _ in pairs(misses) do
    count = count + 1
  end

  SVSE.LogMiss = function(origin, english, questID, field)
    if type(english) ~= "string" or english == "" then
      return
    end
    if count >= MAX_ENTRIES then
      return
    end
    local key = SVSE.Normalize(english)
    if key == "" or misses[key] then
      return
    end
    count = count + 1
    misses[key] = {
      origin = origin,
      quest = questID,
      field = field,
      seen = GetTime and math.floor(GetTime()) or 0,
    }
  end
end)
