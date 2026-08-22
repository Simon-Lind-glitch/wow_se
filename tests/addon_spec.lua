-- Load the whole addon under a stubbed client and check it renders.
--
-- This is the closest thing to launching the game that can run in CI. It
-- catches the failures that matter most and that a syntax check cannot see: a
-- hook erroring at load because a global is missing, the generated data not
-- reaching the lookup tables, and the miss path returning something other than
-- the English.
--
-- The stub environment is deliberately sparse. Most of the client is absent,
-- which is exactly the condition the addon has to survive after a patch renames
-- a frame (spec §3: never error, never block).

local ADDON_FILES = {
  "core.lua",
  "render.lua",
  "locale/globalstrings.lua",
  "data/quests_durotar.lua",
  "hooks/quest.lua",
  "hooks/gossip.lua",
  "hooks/tooltip.lua",
  "devtools/misslog.lua",
}

local function stubFrame()
  local frame = { events = {}, scripts = {} }
  function frame:RegisterEvent(event)
    self.events[event] = true
  end
  function frame:SetScript(name, handler)
    self.scripts[name] = handler
  end
  function frame:HookScript(name, handler)
    self.scripts[name] = handler
  end
  frame.IsShown = function()
    return false
  end
  frame.GetName = function()
    return nil
  end
  function frame:SetText(text)
    self.text = text
  end
  function frame:GetText()
    return self.text
  end
  return frame
end

local function stubClient()
  local created = {}
  _G.CreateFrame = function()
    local frame = stubFrame()
    created[#created + 1] = frame
    return frame
  end
  _G.hooksecurefunc = function() end
  _G.GetTime = function()
    return 1000
  end
  _G.SlashCmdList = {}
  _G.WoWsvSEDB = nil
  _G.GameTooltip = stubFrame()
  return created
end

local function loadAddon()
  local created = stubClient()
  local SVSE = {}
  for _, file in ipairs(ADDON_FILES) do
    local chunk = assert(loadfile("addon/WoWsvSE/" .. file), "missing " .. file)
    chunk("WoWsvSE", SVSE)
  end
  return SVSE, created
end

describe("the addon", function()
  it("loads every file without erroring in a bare environment", function()
    assert.has_no.errors(loadAddon)
  end)

  it("registers the quest, gossip and login events", function()
    local _, created = loadAddon()
    local seen = {}
    for _, frame in ipairs(created) do
      for event in pairs(frame.events) do
        seen[event] = true
      end
    end
    assert.is_true(seen.QUEST_DETAIL)
    assert.is_true(seen.QUEST_PROGRESS)
    assert.is_true(seen.QUEST_COMPLETE)
    assert.is_true(seen.GOSSIP_SHOW)
    assert.is_true(seen.PLAYER_LOGIN)
  end)

  it("never registers a chat event", function()
    -- Spec §2. `make guard` greps for this too; this checks the running
    -- behaviour rather than the source text.
    local _, created = loadAddon()
    for _, frame in ipairs(created) do
      for event in pairs(frame.events) do
        assert.is_nil(event:match("^CHAT_MSG"), "registered " .. event)
      end
    end
  end)

  it("picks a tooltip API by detection", function()
    local SVSE = loadAddon()
    assert.are.equal("OnTooltipSetItem", SVSE.tooltipApi)
  end)

  it("assigns Swedish GlobalStrings", function()
    loadAddon()
    assert.are.equal("Acceptera", _G.ACCEPT)
    assert.are.equal("Lämna in uppdrag", _G.COMPLETE_QUEST)
    assert.are.equal("Din väska är full.", _G.ERR_INV_FULL)
  end)

  it("keeps format specifiers in the GlobalStrings it assigns", function()
    loadAddon()
    assert.are.equal("Grattis, du har nått nivå %d!", _G.LEVEL_UP)
    assert.is_truthy(_G.ABANDON_QUEST_CONFIRM:find("%%s"))
  end)

  it("loads the Durotar quests into the lookup table", function()
    local SVSE = loadAddon()
    local quests, strings = SVSE.Count()
    assert.is_true(quests >= 16, "expected the zone's quests, got " .. quests)
    assert.are.equal(0, strings) -- no free-text strings extracted yet
    assert.is_truthy(SVSE.quests[788])
    assert.is_truthy(SVSE.quests[788].objectives:find("fläckiga vildsvin"))
  end)

  describe("rendering", function()
    local SVSE
    before_each(function()
      SVSE = loadAddon()
    end)

    it("shows Swedish with the English beneath it in grey", function()
      local english = "Kill 10 Mottled Boars then return to Gornek at the Den."
      local out = SVSE.RenderQuest("objective", 788, "objectives", english)
      assert.is_truthy(out:find("fläckiga vildsvin"), out)
      assert.is_truthy(out:find("|cff808080", 1, true), "missing grey escape")
      assert.is_truthy(out:find(english, 1, true), "missing the English original")
    end)

    it("shows Swedish alone when dual language is off", function()
      SVSE.Settings().dual = false
      local out = SVSE.RenderQuest("objective", 788, "objectives", "whatever")
      assert.is_nil(out:find("|cff808080", 1, true))
      assert.is_truthy(out:find("fläckiga vildsvin"))
    end)

    it("can be turned off for one category only", function()
      SVSE.Settings().categories.objective = false
      local out = SVSE.RenderQuest("objective", 788, "objectives", "whatever")
      assert.is_nil(out:find("|cff808080", 1, true))
    end)

    it("renders the English unchanged on a miss", function()
      -- Spec §7: never an error, never an empty string, never a block.
      local english = "A quest that was never translated."
      assert.are.equal(english, SVSE.RenderQuest("quest", 999999, "description", english))
      assert.are.equal(english, SVSE.Render("gossip", english))
    end)

    it("fails closed on an unknown origin", function()
      local english = "Kill 10 Mottled Boars then return to Gornek at the Den."
      -- An untagged string must render as-is even though a translation exists.
      assert.are.equal(english, SVSE.Render("combatlog", english))
      assert.are.equal(english, SVSE.Render(nil, english))
    end)

    it("survives nil and empty input", function()
      assert.is_nil(SVSE.Render("quest", nil))
      assert.are.equal("", SVSE.Render("quest", ""))
      assert.is_nil(SVSE.RenderQuest("quest", 788, "description", nil))
    end)

    it("finds a quest by id even when the English has drifted", function()
      -- The ID is preferred over the text, so a wording change upstream still
      -- resolves (spec §7).
      local out = SVSE.RenderQuest("objective", 788, "objectives", "totally different wording")
      assert.is_truthy(out:find("fläckiga vildsvin"))
    end)
  end)

  describe("the miss logger", function()
    it("stays silent unless the debug flag is set", function()
      local SVSE, created = loadAddon()
      SVSE.Settings().debug = false
      for _, frame in ipairs(created) do
        if frame.events.PLAYER_LOGIN and frame.scripts.OnEvent then
          frame.scripts.OnEvent()
        end
      end
      SVSE.Render("gossip", "Something untranslated")
      assert.are.equal(0, #_G.WoWsvSEDB.misses)
      assert.is_nil(next(_G.WoWsvSEDB.misses))
    end)

    it("records misses once each when debugging", function()
      local SVSE, created = loadAddon()
      SVSE.Settings().debug = true
      for _, frame in ipairs(created) do
        if frame.events.PLAYER_LOGIN and frame.scripts.OnEvent then
          frame.scripts.OnEvent()
        end
      end
      SVSE.Render("gossip", "Something untranslated")
      SVSE.Render("gossip", "Something untranslated")
      SVSE.Render("gossip", "Another one")
      local count = 0
      for _ in pairs(_G.WoWsvSEDB.misses) do
        count = count + 1
      end
      assert.are.equal(2, count)
      assert.are.equal("gossip", _G.WoWsvSEDB.misses["Another one"].origin)
    end)
  end)
end)
