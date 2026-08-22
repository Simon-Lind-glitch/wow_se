-- Authoritative WoW global list for the addon tree.
-- The game runs Lua 5.1; keep this in lockstep with the editor's
-- Lua.diagnostics.globals in .devcontainer/devcontainer.json.
std = "lua51"
max_line_length = 120
codes = true

-- Generated data files are enormous machine-written tables (spec §4:
-- "Never hand-edit them; fix the toolchain and regenerate"). Linting them
-- costs minutes and tells us nothing.
exclude_files = {
  "addon/WoWsvSE/data/**",
  "tools/cache/**",
}

read_globals = {
  -- Sandbox / hooking
  "hooksecurefunc", "issecurevariable", "CreateFrame", "GetTime",
  -- Client info
  "GetLocale", "GetBuildInfo", "UnitName", "UnitClass", "UnitRace", "UnitSex",
  -- Quest API (spec §7)
  "GetQuestText", "GetObjectiveText", "GetRewardText", "GetProgressText",
  "GetTitleText", "GetQuestID", "GetQuestLogQuestText", "GetQuestLogTitle",
  "GetNumQuestLeaderBoards", "GetQuestLogLeaderBoard",
  -- Gossip. C_GossipInfo on modern-engine builds, GetGossipText on older ones;
  -- hooks/gossip.lua detects which is present (spec §0).
  "C_GossipInfo", "GetGossipText", "GossipGreetingText",
  -- Quest log
  "GetQuestLogSelection", "QuestLogQuestDescription", "QuestLogObjectivesText",
  "QuestLog_UpdateQuestDetails",
  -- Tooltips (which one exists depends on the target flavor — verify per §7)
  "GameTooltip", "TooltipDataProcessor",
  -- Frames we write into
  "QuestInfoDescriptionText", "QuestInfoObjectivesText", "QuestInfoRewardText",
  "QuestInfoTitleHeader", "QuestLogQuestTitle", "QuestProgressText",
  -- Panels we test for visibility, and the display function we hook
  "QuestFrameDetailPanel", "QuestFrameRewardPanel", "QuestInfo_Display",
  -- Enum table, present only where TooltipDataProcessor is
  "Enum",
  -- Misc
  "string", "table", "math", "wipe", "strtrim", "format",
}

globals = {
  -- SavedVariables declared in the .toc
  "WoWsvSEDB",
  -- Addons register commands by writing into this table; that is the API.
  "SlashCmdList",
  -- Slash command registration writes these
  "SLASH_SVSE1", "SLASH_SVSE2",
}

-- Phase 1 reassigns arbitrary Blizzard GlobalStrings by name. Every single
-- assignment in this generated file is a legitimate write to a global that
-- luacheck cannot know about, so silence 111/112 here only.
files["addon/WoWsvSE/locale/globalstrings.lua"] = {
  ignore = { "111", "112" },
}

-- Tests run under busted.
files["tests/**"] = {
  std = "+busted",
}
