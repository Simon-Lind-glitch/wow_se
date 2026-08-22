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
  dual = true,
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
  if db.dual == nil then
    db.dual = DEFAULTS.dual
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
      "/svse dual — visa engelska under svenskan (nu: " .. (db.dual and "på" or "av") .. ")"
    )
    report("/svse quest|objective|gossip|tooltip — slå av eller på en kategori")
    report("/svse debug — logga saknade texter (bara för utveckling)")
    return
  end

  if command == "dual" then
    db.dual = not db.dual
    report("engelska under svenskan: " .. (db.dual and "på" or "av"))
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
