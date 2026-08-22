-- Rendering: Swedish on screen, the English original one hover away.
--
-- Deviation from §7, decided after in-game testing. The spec asks for the
-- English appended beneath the Swedish in smaller grey type, default on. Tried;
-- rejected by the requester as cluttered and confusing to read. It also doubles
-- the height of every quest paragraph in a frame that was laid out for one
-- language.
--
-- The intent §7 was after — a reading aid rather than a crutch, with a path off
-- it — is kept by two other means:
--
--   * the English original appears in a tooltip when you point at the text, so
--     it is one gesture away instead of permanently in the way
--   * each category can be switched back to English entirely (`/svse objective`),
--     which is how the kids step off the addon as their reading improves
--
-- Nothing is composed into the frame text any more, which also removes a whole
-- class of layout problem: we write exactly as many lines as the client did.

local _, SVSE = ...

--- Is this category being shown in Swedish at all?
--
-- Turning one off renders the client's own English. That is the path off the
-- addon: objectives first, then descriptions, category by category.
function SVSE.CategoryEnabled(origin)
  return SVSE.Settings().categories[origin] ~= false
end

--- What to actually put in the frame.
function SVSE.Compose(swedish, english, origin)
  if type(swedish) ~= "string" or swedish == "" then
    return SVSE.Expand(english)
  end
  if not SVSE.CategoryEnabled(origin) then
    return SVSE.Expand(english)
  end
  return SVSE.Expand(swedish)
end

--- Render a free-text string. Falls back to the English unchanged.
function SVSE.Render(origin, english)
  if type(english) ~= "string" or english == "" then
    return english
  end
  local swedish = SVSE.Lookup(origin, english)
  if not swedish then
    SVSE.LogMiss(origin, english)
    -- Even on a miss the English needs expanding: the raw API text carries the
    -- same tokens, and we are the ones writing it into the frame.
    return SVSE.Expand(english)
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
    return SVSE.Expand(english)
  end
  return SVSE.Compose(swedish, english, origin)
end

--- Show the English original in a tooltip when the mouse is over `region`.
--
-- A FontString is not a frame and cannot take mouse events, so an invisible
-- frame is anchored over it. One overlay per region, reused: creating a frame
-- per quest would leak a frame for every quest the kids ever read.
function SVSE.AttachOriginal(region, english)
  if not region or type(english) ~= "string" or english == "" then
    return
  end
  if not SVSE.Settings().hover then
    if region.svseOverlay then
      region.svseOverlay:Hide()
    end
    return
  end

  local overlay = region.svseOverlay
  if not overlay then
    local parent = region.GetParent and region:GetParent()
    if not parent or not CreateFrame then
      return
    end
    overlay = CreateFrame("Frame", nil, parent)
    overlay:EnableMouse(true)
    overlay:SetScript("OnEnter", function(self)
      if not self.english or self.english == "" or not GameTooltip then
        return
      end
      GameTooltip:SetOwner(self, "ANCHOR_BOTTOMRIGHT")
      GameTooltip:AddLine("Engelska originalet", 1, 0.82, 0)
      GameTooltip:AddLine(self.english, 0.85, 0.85, 0.85, true)
      GameTooltip:Show()
    end)
    overlay:SetScript("OnLeave", function()
      if GameTooltip then
        GameTooltip:Hide()
      end
    end)
    region.svseOverlay = overlay
  end

  overlay.english = SVSE.Expand(english)
  overlay:ClearAllPoints()
  overlay:SetAllPoints(region)
  overlay:Show()
end
