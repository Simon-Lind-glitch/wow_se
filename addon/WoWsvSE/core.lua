-- Lookup, settings and slash commands.
--
-- Nothing here touches a Blizzard API at load time. That is deliberate: it
-- keeps this file loadable under plain Lua 5.1 so `tests/normalize_spec.lua`
-- can check that Normalize agrees with the Python implementation. The moment
-- this file calls CreateFrame at file scope, that test becomes impossible.

local ADDON, SVSE = ...

SVSE.name = ADDON

-- Filled by the generated data files.
SVSE.quests = SVSE.quests or {}
SVSE.text = SVSE.text or {}

-- Origins we are willing to translate. Anything not on this list renders
-- unchanged (spec §7: allowlist by origin, fail closed). An untagged string is
-- a bug in a hook, and rendering it as-is is the safe failure.
local ORIGINS = {
  title = true,
  quest = true,
  objective = true,
  gossip = true,
  tooltip = true,
}
SVSE.ORIGINS = ORIGINS

local DEFAULTS = {
  -- English original in a tooltip on hover. This is the reading aid §7 asks
  -- for; the inline grey line it originally specified was tried and rejected
  -- as cluttered (see render.lua).
  hover = true,
  -- Seconds the pointer must rest before the English appears. Long on purpose:
  -- scrolling a quest drags the pointer across the text repeatedly.
  hoverDelay = 5,
  debug = false,
}

--- Reduce a client string to its lookup key.
--
-- Must agree exactly with `normalize()` in tools/common/normalize.py or every
-- lookup misses. Both are checked against tests/fixtures/normalize_vectors.lua.
--
-- Only ASCII whitespace is touched: Lua's %s is ASCII-only, and the Python side
-- is restricted to match.
function SVSE.Normalize(text)
  if type(text) ~= "string" or text == "" then
    return ""
  end
  -- Keep a hyperlink's display text, drop its payload.
  text = text:gsub("|H.-|h(.-)|h", "%1")
  text = text:gsub("|T.-|t", "")
  text = text:gsub("|c%x%x%x%x%x%x%x%x", "")
  text = text:gsub("|r", "")
  text = text:gsub("%s+", " ")
  text = text:gsub("^ +", "")
  text = text:gsub(" +$", "")
  return text
end

--- SavedVariables, created on first use.
--
-- Read lazily rather than at load: WoWsvSEDB does not exist until the client
-- has loaded saved variables, and touching it early would silently discard the
-- kids' settings on every login.
function SVSE.Settings()
  if type(WoWsvSEDB) ~= "table" then
    WoWsvSEDB = {}
  end
  local db = WoWsvSEDB
  if db.hover == nil then
    db.hover = DEFAULTS.hover
  end
  if type(db.hoverDelay) ~= "number" then
    db.hoverDelay = DEFAULTS.hoverDelay
  end
  if db.debug == nil then
    db.debug = DEFAULTS.debug
  end
  if type(db.categories) ~= "table" then
    db.categories = {}
  end
  for origin in pairs(ORIGINS) do
    if db.categories[origin] == nil then
      db.categories[origin] = true
    end
  end
  if type(db.misses) ~= "table" then
    db.misses = {}
  end
  return db
end

--- Swedish for a free-text string, or nil.
function SVSE.Lookup(origin, english)
  if not ORIGINS[origin] then
    return nil
  end
  local key = SVSE.Normalize(english)
  if key == "" then
    return nil
  end
  return SVSE.text[key]
end

--- Swedish for one field of a known quest, or nil.
--
-- Preferred over the text lookup wherever the game hands us an ID: it is
-- stable across wording changes and cannot collide (spec §7).
function SVSE.LookupQuest(questID, field)
  if type(questID) ~= "number" or questID <= 0 then
    return nil
  end
  local quest = SVSE.quests[questID]
  if not quest then
    return nil
  end
  return quest[field]
end

--- Expand the quest tokens the client would have expanded itself.
--
-- The client substitutes $N, $B, $C, $R and $G only in text it receives from
-- the server. Text an addon writes into a FontString is drawn literally, so a
-- translation carrying $N renders as the three characters "$N" in front of the
-- player. We therefore expand them here, at display time.
--
-- The stored translation keeps its tokens: the cache stays faithful to the
-- source, and expansion is a property of rendering, not of the data.
--
-- Format specifiers (%s, %d) are deliberately NOT touched. Those are consumed
-- by string.format in whatever Blizzard code owns the string, and expanding
-- them here would corrupt it.
function SVSE.Expand(text)
  if type(text) ~= "string" or text == "" then
    return text
  end
  if not text:find("$", 1, true) then
    return text
  end

  -- $G male:female; and $g male:female; — resolved before the single-letter
  -- tokens, because its branches may themselves contain them.
  local sex = UnitSex and UnitSex("player") or nil
  text = text:gsub("%$[Gg]%s*([^:;]*):([^;]*);", function(male, female)
    -- 2 is male, 3 is female. Anything else (unknown, or no API in tests)
    -- keeps the male branch rather than showing both or neither.
    if sex == 3 then
      return female
    end
    return male
  end)

  local name = (UnitName and UnitName("player")) or ""
  local class = (UnitClass and UnitClass("player")) or ""
  local race = (UnitRace and UnitRace("player")) or ""

  text = text:gsub("%$[Bb]", "\n")
  text = text:gsub("%$[Nn]", name)
  text = text:gsub("%$[Cc]", class)
  text = text:gsub("%$[Rr]", race)
  return text
end

--- Replaced by devtools/misslog.lua when the debug flag is set.
function SVSE.LogMiss() end

function SVSE.Count()
  local quests, strings = 0, 0
  for _ in pairs(SVSE.quests) do
    quests = quests + 1
  end
  for _ in pairs(SVSE.text) do
    strings = strings + 1
  end
  return quests, strings
end

local function report(message)
  print("|cff66bbaaWoWsvSE|r " .. message)
end
SVSE.Report = report

function SVSE.HandleCommand(input)
  local db = SVSE.Settings()
  local command, argument = string.match(input or "", "^(%S*)%s*(.-)$")
  command = string.lower(command or "")

  if command == "" or command == "help" then
    local quests, strings = SVSE.Count()
    report(("%d uppdrag och %d texter laddade."):format(quests, strings))
    report(
      "/svse hover — visa engelskan när du pekar på texten (nu: "
        .. (db.hover and "på" or "av")
        .. ")"
    )
    report("/svse quest|objective|title|gossip|tooltip — svenska eller engelska")
    report("/svse debug — logga saknade texter (bara för utveckling)")
    return
  end

  if command == "hover" then
    -- `/svse hover 2` sets the delay; bare `/svse hover` turns it off and on.
    local seconds = tonumber(argument)
    if seconds and seconds >= 0 then
      db.hoverDelay = seconds
      db.hover = seconds > 0
      report(("engelskan visas efter %s sekunder"):format(tostring(seconds)))
      return
    end
    db.hover = not db.hover
    report("engelskan vid pekning: " .. (db.hover and "på" or "av"))
    return
  end

  if command == "debug" then
    db.debug = not db.debug
    report("felsökning: " .. (db.debug and "på" or "av") .. " (starta om spelet)")
    return
  end

  if ORIGINS[command] then
    db.categories[command] = not db.categories[command]
    report(command .. ": " .. (db.categories[command] and "svenska" or "engelska"))
    return
  end

  report("okänt kommando: " .. command .. " — skriv /svse för hjälp")
  if argument ~= "" then
    report("(ignorerade: " .. argument .. ")")
  end
end

-- Assigning these is a plain table write, safe at load.
if SlashCmdList then
  SLASH_SVSE1 = "/svse"
  SLASH_SVSE2 = "/sv"
  SlashCmdList["SVSE"] = SVSE.HandleCommand
end
