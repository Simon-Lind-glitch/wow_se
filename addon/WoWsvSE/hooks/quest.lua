-- Quest text: the detail pane, the progress and reward pages, and the log.
--
-- `hooksecurefunc` only, never replacement (spec §3). Overwriting a Blizzard
-- function taints the execution path, and a tainted path breaks protected
-- actions in combat — which for a nine-year-old means abilities that silently
-- stop working in a fight.
--
-- Every global is checked before use. This addon has to survive a client patch
-- renaming a frame by doing nothing, not by erroring on login.

local _, SVSE = ...

--- Write rendered text into a FontString, if there is anything to change.
local function apply(frame, origin, questID, field, english)
  if not frame or not frame.SetText then
    return
  end
  if type(english) ~= "string" or english == "" then
    return
  end
  local rendered = SVSE.RenderQuest(origin, questID, field, english)
  if rendered and rendered ~= english then
    frame:SetText(rendered)
  end
end

local function currentQuestID()
  if GetQuestID then
    local id = GetQuestID()
    if type(id) == "number" and id > 0 then
      return id
    end
  end
  return nil
end

--- The quest giver's offer page.
local function renderDetail()
  local questID = currentQuestID()
  apply(QuestInfoTitleHeader, "title", questID, "title", GetTitleText and GetTitleText())
  apply(QuestInfoDescriptionText, "quest", questID, "description", GetQuestText and GetQuestText())
  apply(
    QuestInfoObjectivesText,
    "objective",
    questID,
    "objectives",
    GetObjectiveText and GetObjectiveText()
  )
end

--- "You are not finished yet" page.
local function renderProgress()
  local questID = currentQuestID()
  apply(QuestProgressText, "quest", questID, "progress", GetProgressText and GetProgressText())
end

--- The hand-in page.
local function renderComplete()
  local questID = currentQuestID()
  apply(QuestInfoRewardText, "quest", questID, "completion", GetRewardText and GetRewardText())
  apply(QuestInfoTitleHeader, "title", questID, "title", GetTitleText and GetTitleText())
end

local EVENTS = {
  QUEST_DETAIL = renderDetail,
  QUEST_PROGRESS = renderProgress,
  QUEST_COMPLETE = renderComplete,
}

local frame = CreateFrame("Frame")
for event in pairs(EVENTS) do
  frame:RegisterEvent(event)
end
frame:SetScript("OnEvent", function(_, event)
  local handler = EVENTS[event]
  if handler then
    handler()
  end
end)

-- Blizzard re-renders the pane after the event fires, which would put the
-- English back. Running again afterwards is why this is a hook rather than only
-- an event handler.
if QuestInfo_Display then
  hooksecurefunc("QuestInfo_Display", function()
    if QuestFrameDetailPanel and QuestFrameDetailPanel:IsShown() then
      renderDetail()
    elseif QuestFrameRewardPanel and QuestFrameRewardPanel:IsShown() then
      renderComplete()
    end
  end)
end

-- The quest log's own detail pane reads through a different API.
if QuestLog_UpdateQuestDetails then
  hooksecurefunc("QuestLog_UpdateQuestDetails", function()
    if not GetQuestLogQuestText then
      return
    end
    local description, objectives = GetQuestLogQuestText()
    local questID = nil
    if GetQuestLogSelection and GetQuestLogTitle then
      local _, _, _, _, _, _, _, id = GetQuestLogTitle(GetQuestLogSelection())
      if type(id) == "number" and id > 0 then
        questID = id
      end
    end
    apply(QuestLogQuestDescription, "quest", questID, "description", description)
    apply(QuestLogObjectivesText, "objective", questID, "objectives", objectives)
  end)
end
