-- Dual-language composition.
--
-- Swedish on top, English beneath in grey. Default on, per spec §7: the point
-- is to be a reading aid the kids can grow out of, not a crutch they depend on.
--
-- Known deviation from §7: the spec asks for the English at ~85% size. A
-- FontString renders in a single font, so mixing sizes inside one means adding
-- a second FontString to every frame we write into. Colour is achievable with
-- an inline escape and gets most of the effect; the size difference is left for
-- when there is a real frame to attach.

local _, SVSE = ...

local GREY = "|cff808080"
local RESET = "|r"

--- Should this origin show the English line?
function SVSE.DualEnabled(origin)
  local db = SVSE.Settings()
  if not db.dual then
    return false
  end
  return db.categories[origin] ~= false
end

function SVSE.Compose(swedish, english, origin)
  if type(swedish) ~= "string" or swedish == "" then
    return english
  end
  if not SVSE.DualEnabled(origin) or type(english) ~= "string" or english == "" then
    return swedish
  end
  if swedish == english then
    return swedish
  end
  return swedish .. "\n" .. GREY .. english .. RESET
end

--- Render a free-text string. Falls back to the English unchanged.
function SVSE.Render(origin, english)
  if type(english) ~= "string" or english == "" then
    return english
  end
  local swedish = SVSE.Lookup(origin, english)
  if not swedish then
    SVSE.LogMiss(origin, english)
    return english
  end
  return SVSE.Compose(swedish, english, origin)
end

--- Render one field of a quest, preferring the quest ID over the text lookup.
function SVSE.RenderQuest(origin, questID, field, english)
  if type(english) ~= "string" or english == "" then
    return english
  end
  local swedish = SVSE.LookupQuest(questID, field) or SVSE.Lookup(origin, english)
  if not swedish then
    SVSE.LogMiss(origin, english, questID, field)
    return english
  end
  return SVSE.Compose(swedish, english, origin)
end
