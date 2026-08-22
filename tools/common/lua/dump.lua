-- Load an upstream Lua file as data and print it as JSON on stdout.
--
-- Both of our upstream string sources (the client's GlobalStrings dump and
-- Questie's quest database) are Lua source, not data formats. Regex-parsing
-- them is how you end up mis-handling an escaped quote in one quest out of two
-- hundred and never noticing, so we run them in the interpreter the game uses.
--
-- usage:  lua5.1 dump.lua <file.lua> [global-to-dump | --return]
--
-- With no global named, every string-valued global the chunk assigned is
-- dumped (that is the GlobalStrings shape). With one named, that value is
-- dumped whole (that is the Questie shape). With --return, the chunk's own
-- return value is dumped (that is the test-fixture shape).

local path, wanted = ...
if not path then
  io.stderr:write("usage: dump.lua <file.lua> [global]\n")
  os.exit(2)
end

local dir = arg[0]:match("^(.*)/[^/]*$") or "."
package.path = dir .. "/?.lua;" .. package.path
local encode = require("json").encode

local chunk, err = loadfile(path)
if not chunk then
  io.stderr:write("load failed: " .. tostring(err) .. "\n")
  os.exit(1)
end

-- Writes land in `env`; reads fall through to the real globals so a file that
-- calls string.format or references an earlier constant still runs.
local env = setmetatable({}, { __index = _G })
setfenv(chunk, env)

local ok, returned = pcall(chunk)
if not ok then
  io.stderr:write("execute failed: " .. tostring(returned) .. "\n")
  os.exit(1)
end

-- `--return` dumps what the chunk returned rather than what it assigned. Test
-- fixtures are written as `return { ... }`, which is the natural shape for a
-- Lua data file but assigns no global.
if wanted == "--return" then
  if returned == nil then
    io.stderr:write("chunk returned nothing\n")
    os.exit(1)
  end
  io.write(encode(returned))
  io.write("\n")
  return
end

if wanted then
  local value = env[wanted]
  if value == nil then
    -- Some upstream files stash their payload on a module table rather than a
    -- bare global; try one level of dotted lookup before giving up.
    local head, tail = wanted:match("^([^.]+)%.(.+)$")
    if head and type(env[head]) == "table" then
      value = env[head][tail]
    end
  end
  if value == nil then
    io.stderr:write("global not found: " .. wanted .. "\n")
    os.exit(1)
  end
  io.write(encode(value))
else
  local strings = {}
  for k, v in pairs(env) do
    if type(k) == "string" and type(v) == "string" then
      strings[k] = v
    end
  end
  io.write(encode(strings))
end
io.write("\n")
