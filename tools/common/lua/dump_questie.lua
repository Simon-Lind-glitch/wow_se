-- Load Questie's quest database and print it as JSON.
--
-- Questie needs its own loader for two reasons. It expects the addon
-- environment (`QuestieLoader:ImportModule`), and it stores the actual quest
-- table as a *string* containing a Lua chunk:
--
--     QuestieDB.questData = [[return { [123] = {"Name", ...}, ... }]]
--
-- so the payload has to be loadstring'd after the file itself runs. This is
-- exactly the case where regex-parsing would be a mistake.
--
-- usage:  lua5.1 dump_questie.lua <tbcQuestDB.lua> <questData|questKeys>

local path, which = ...
if not path or not which then
  io.stderr:write("usage: dump_questie.lua <file.lua> <questData|questKeys>\n")
  os.exit(2)
end

local dir = arg[0]:match("^(.*)/[^/]*$") or "."
package.path = dir .. "/?.lua;" .. package.path
local encode = require("json").encode

-- Stand-in for the addon loader. Returns one shared table per module name, so
-- `QuestieDB.questData = ...` lands somewhere we can read.
local modules = {}
local QuestieLoader = {
  ImportModule = function(_, name)
    modules[name] = modules[name] or {}
    return modules[name]
  end,
}

local env = setmetatable({ QuestieLoader = QuestieLoader }, { __index = _G })

local chunk, err = loadfile(path)
if not chunk then
  io.stderr:write("load failed: " .. tostring(err) .. "\n")
  os.exit(1)
end
setfenv(chunk, env)
local ok, runtime_err = pcall(chunk)
if not ok then
  io.stderr:write("execute failed: " .. tostring(runtime_err) .. "\n")
  os.exit(1)
end

local db = modules["QuestieDB"]
if not db then
  io.stderr:write("QuestieDB module was never imported\n")
  os.exit(1)
end

local value = db[which]
if value == nil then
  io.stderr:write("QuestieDB." .. which .. " not found\n")
  os.exit(1)
end

-- The compiled databases arrive as a chunk in a string; the key tables arrive
-- as plain tables.
if type(value) == "string" then
  local payload, load_err = loadstring(value)
  if not payload then
    io.stderr:write("questData chunk failed to compile: " .. tostring(load_err) .. "\n")
    os.exit(1)
  end
  setfenv(payload, {})
  local decoded_ok, decoded = pcall(payload)
  if not decoded_ok then
    io.stderr:write("questData chunk failed to run: " .. tostring(decoded) .. "\n")
    os.exit(1)
  end
  value = decoded
end

io.write(encode(value))
io.write("\n")
