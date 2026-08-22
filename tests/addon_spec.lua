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
  "hooks/frames.lua",
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
  frame.EnableMouse = function() end
  frame.ClearAllPoints = function() end
  frame.SetAllPoints = function() end
  frame.Show = function(self)
    self.shown = true
  end
  frame.Hide = function(self)
    self.shown = false
  end
  frame.GetParent = function()
    return nil
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
  _G.GameTooltip.SetOwner = function() end
  _G.GameTooltip.AddLine = function() end
  _G.GameTooltip.Show = function() end
  _G.GameTooltip.Hide = function() end
  _G.UnitName = function()
    return "Grommash"
  end
  _G.UnitClass = function()
    return "krigare"
  end
  _G.UnitRace = function()
    return "orch"
  end
  _G.UnitSex = function()
    return 2
  end
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

  describe("token expansion", function()
    local SVSE
    before_each(function()
      SVSE = loadAddon()
    end)

    it("expands the tokens the client would have expanded itself", function()
      -- The client only substitutes these in text it receives from the server.
      -- Text an addon writes into a FontString is drawn literally, so leaving
      -- them alone puts "$N" in front of the player.
      assert.are.equal("Hej Grommash!", SVSE.Expand("Hej $N!"))
      assert.are.equal("du är krigare", SVSE.Expand("du är $C"))
      assert.are.equal("du är orch", SVSE.Expand("du är $R"))
      assert.are.equal("en\ntvå", SVSE.Expand("en$Btvå"))
    end)

    it("expands the lowercase spellings too", function()
      assert.are.equal("Hej Grommash!", SVSE.Expand("Hej $n!"))
      assert.are.equal("en\ntvå", SVSE.Expand("en$btvå"))
    end)

    it("picks the gender branch from the player's sex", function()
      assert.are.equal("en stolt pojke", SVSE.Expand("en stolt $Gpojke:flicka;"))
      _G.UnitSex = function()
        return 3
      end
      assert.are.equal("en stolt flicka", SVSE.Expand("en stolt $Gpojke:flicka;"))
    end)

    it("leaves format specifiers alone", function()
      -- These are consumed by string.format in whatever code owns the string;
      -- expanding them here would corrupt it.
      assert.are.equal("nivå %d", SVSE.Expand("nivå %d"))
      assert.are.equal("%1$s och %2$d", SVSE.Expand("%1$s och %2$d"))
    end)

    it("is a no-op on text with no tokens", function()
      local plain = "Döda 10 fläckiga vildsvin."
      assert.are.equal(plain, SVSE.Expand(plain))
      assert.is_nil(SVSE.Expand(nil))
    end)
  end)

  describe("rendering", function()
    local SVSE
    before_each(function()
      SVSE = loadAddon()
    end)

    it("puts Swedish in the frame and nothing else", function()
      -- No inline English: the grey second line was rejected in testing as
      -- cluttered, and it doubled the height of every paragraph.
      local english = "Kill 10 Mottled Boars then return to Gornek at the Den."
      local out = SVSE.RenderQuest("objective", 788, "objectives", english)
      assert.is_truthy(out:find("fläckiga vildsvin"), out)
      assert.is_nil(out:find("|cff808080", 1, true), "grey escape should be gone")
      assert.is_nil(out:find(english, 1, true), "English should not be inlined")
    end)

    it("expands tokens in the Swedish it writes", function()
      -- Regression: quest prose from the world DB carries $N and $B, and they
      -- were rendering as literal characters in game.
      local out = SVSE.RenderQuest("quest", 788, "progress", "whatever")
      assert.is_nil(out:find("$N", 1, true), "raw $N reached the frame: " .. out)
      assert.is_nil(out:find("$B", 1, true), "raw $B reached the frame")
      assert.is_truthy(out:find("Grommash", 1, true), "player name not substituted")
    end)

    it("hands back the English when a category is switched off", function()
      -- The path off the addon: objectives first, then the rest (spec §7).
      SVSE.Settings().categories.objective = false
      local english = "Kill 10 Mottled Boars then return to Gornek at the Den."
      assert.are.equal(english, SVSE.RenderQuest("objective", 788, "objectives", english))
    end)

    it("renders the English unchanged on a miss", function()
      -- Spec §7: never an error, never an empty string, never a block.
      local english = "A quest that was never translated."
      assert.are.equal(english, SVSE.RenderQuest("quest", 999999, "description", english))
      assert.are.equal(english, SVSE.Render("gossip", english))
    end)

    it("fails closed on an unknown origin", function()
      local english = "Kill 10 Mottled Boars then return to Gornek at the Den."
      -- An untagged string renders as-is even though a translation exists.
      assert.are.equal(english, SVSE.Render("combatlog", english))
      assert.are.equal(english, SVSE.Render(nil, english))
    end)

    it("survives nil and empty input", function()
      assert.is_nil(SVSE.Render("quest", nil))
      assert.are.equal("", SVSE.Render("quest", ""))
      assert.is_nil(SVSE.RenderQuest("quest", 788, "description", nil))
    end)

    it("finds a quest by id even when the English has drifted", function()
      local out = SVSE.RenderQuest("objective", 788, "objectives", "totally different wording")
      assert.is_truthy(out:find("fläckiga vildsvin"))
    end)
  end)

  describe("the hover original", function()
    local SVSE
    before_each(function()
      SVSE = loadAddon()
    end)

    it("attaches one reusable overlay carrying the English", function()
      local region = stubFrame()
      region.GetParent = function()
        return stubFrame()
      end
      region.ClearAllPoints = function() end
      region.SetAllPoints = function() end

      SVSE.AttachOriginal(region, "Kill 10 Mottled Boars.")
      local overlay = region.svseOverlay
      assert.is_truthy(overlay, "no overlay created")
      assert.are.equal("Kill 10 Mottled Boars.", overlay.english)

      -- Called again for the next quest: same frame, new text. Creating one per
      -- quest would leak a frame for every quest the kids ever read.
      SVSE.AttachOriginal(region, "Something else.")
      assert.are.equal(overlay, region.svseOverlay)
      assert.are.equal("Something else.", overlay.english)
    end)

    it("expands tokens in the English it shows", function()
      local region = stubFrame()
      region.GetParent = function()
        return stubFrame()
      end
      region.ClearAllPoints = function() end
      region.SetAllPoints = function() end
      SVSE.AttachOriginal(region, "Well done, $N.")
      assert.are.equal("Well done, Grommash.", region.svseOverlay.english)
    end)

    it("does nothing when hover is switched off", function()
      SVSE.Settings().hover = false
      local region = stubFrame()
      SVSE.AttachOriginal(region, "anything")
      assert.is_nil(region.svseOverlay)
    end)
  end)

  describe("relabelling frames built before we loaded", function()
    it("sets a button's text from the Swedish global", function()
      -- Regression: ACCEPT held "Acceptera" but the quest frame still said
      -- "Accept", because FrameXML baked the label in before any addon ran.
      local SVSE = loadAddon()
      local button = stubFrame()
      _G.QuestFrameAcceptButton = button
      SVSE.Relabel()
      assert.are.equal("Acceptera", button:GetText())
      _G.QuestFrameAcceptButton = nil
    end)

    it("skips frame names the client does not have", function()
      -- Frames get renamed between expansions; that must not error on login.
      local SVSE = loadAddon()
      assert.has_no.errors(function()
        SVSE.Relabel()
      end)
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
