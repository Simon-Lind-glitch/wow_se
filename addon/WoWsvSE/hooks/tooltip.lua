-- Item and spell tooltips.
--
-- Which API exists depends on the build, so both paths are wired and the
-- present one wins (spec §7 says to verify before writing; from outside the
-- client, detection *is* the verification).
--
-- Inert until tooltip strings are extracted: with nothing in SVSE.text for the
-- tooltip origin, every lookup misses and the English renders unchanged. With
-- the debug flag on it still records what it saw, which is how the next batch
-- of strings gets found (spec §7, dev-only miss logger).
--
-- Deliberately conservative: only the tooltip's own body lines are considered,
-- and only when a translation already exists. Item links and anything other
-- addons parse are left alone (spec §3).

local _, SVSE = ...

local MAX_LINES = 30

local function translateLines(tooltip)
  if not tooltip or not tooltip.GetName then
    return
  end
  local name = tooltip:GetName()
  if not name then
    return
  end
  for index = 2, MAX_LINES do
    local line = _G[name .. "TextLeft" .. index]
    if not line or not line.GetText then
      break
    end
    local english = line:GetText()
    if type(english) == "string" and english ~= "" then
      local swedish = SVSE.Lookup("tooltip", english)
      if swedish then
        line:SetText(SVSE.Compose(swedish, english, "tooltip"))
      else
        SVSE.LogMiss("tooltip", english)
      end
    end
  end
end

if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum then
  local which = Enum.TooltipDataType
  if which then
    TooltipDataProcessor.AddTooltipPostCall(which.Item, translateLines)
    TooltipDataProcessor.AddTooltipPostCall(which.Spell, translateLines)
    SVSE.tooltipApi = "TooltipDataProcessor"
  end
elseif GameTooltip and GameTooltip.HookScript then
  GameTooltip:HookScript("OnTooltipSetItem", translateLines)
  GameTooltip:HookScript("OnTooltipSetSpell", translateLines)
  SVSE.tooltipApi = "OnTooltipSetItem"
end
