-- Re-apply GlobalStrings to labels that were already drawn.
--
-- Spec §5 says the GlobalStrings are "plain Lua globals, no hooking required —
-- reassign at load". That is true for every string the client reads at the
-- moment it uses it: error messages, tooltip chrome, anything passed through
-- format(). It is NOT true for labels baked into a frame when FrameXML built
-- it, which happens before any addon runs. Those FontStrings already hold the
-- English, and reassigning the global they came from does nothing.
--
-- This is why the quest frame still said "Accept" while ACCEPT itself held
-- "Acceptera". So: after login, set the text again from the (now Swedish)
-- global.
--
-- The table is deliberately small and focused on the quest and gossip flow,
-- which is what is translated. Adding a row is one line, and an unknown frame
-- name is skipped rather than being an error — the client renames frames
-- between expansions and this must not break on login when it happens.

local _, SVSE = ...

local STATIC = {
  -- Quest giver: offer, progress and reward pages.
  QuestFrameAcceptButton = "ACCEPT",
  QuestFrameDeclineButton = "DECLINE",
  QuestFrameCompleteButton = "CONTINUE",
  QuestFrameCompleteQuestButton = "COMPLETE_QUEST",
  QuestFrameGoodbyeButton = "GOODBYE",
  QuestFrameCancelButton = "CANCEL",
  -- Quest log.
  QuestLogFrameAbandonButton = "ABANDON_QUEST_ABBREV",
  QuestLogFrameTrackButton = "TRACK_QUEST_ABBREV",
  QuestLogFrameCancelButton = "CLOSE",
  -- Gossip.
  GossipFrameGreetingGoodbyeButton = "GOODBYE",
  -- Merchant, trainer, and the panels a new player opens most.
  MerchantRepairText = "REPAIR_ITEMS",
  ClassTrainerTrainButton = "TRAIN",
}

local function relabel()
  for frameName, globalKey in pairs(STATIC) do
    local frame = _G[frameName]
    local text = _G[globalKey]
    if frame and frame.SetText and type(text) == "string" and text ~= "" then
      frame:SetText(text)
    end
  end
end
SVSE.Relabel = relabel

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
-- Load-on-demand panels build their frames later, so run again as each arrives.
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", relabel)
