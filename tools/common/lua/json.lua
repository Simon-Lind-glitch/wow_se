-- Minimal JSON encoder for the build-time Lua bridge.
--
-- Shared by dump.lua and dump_questie.lua. Only the value types our upstream
-- sources contain are supported: string, number, boolean, table. Output is key
-- sorted so rebuilds are byte-identical (spec §9.3).

local function encode(value)
  local t = type(value)
  if value == nil then
    return "null"
  elseif t == "boolean" then
    return value and "true" or "false"
  elseif t == "number" then
    -- %.17g round-trips an IEEE double exactly; quest IDs stay integers.
    if value == math.floor(value) and math.abs(value) < 2 ^ 53 then
      return string.format("%d", value)
    end
    return string.format("%.17g", value)
  elseif t == "string" then
    local out = value:gsub('[%c"\\]', function(c)
      if c == '"' then
        return '\\"'
      elseif c == "\\" then
        return "\\\\"
      elseif c == "\n" then
        return "\\n"
      elseif c == "\r" then
        return "\\r"
      elseif c == "\t" then
        return "\\t"
      end
      return string.format("\\u%04x", string.byte(c))
    end)
    -- Bytes >= 0x80 pass through untouched: the sources are UTF-8 and the
    -- consumer decodes UTF-8.
    return '"' .. out .. '"'
  elseif t == "table" then
    local n, maxi, allint = 0, 0, true
    for k in pairs(value) do
      n = n + 1
      if type(k) == "number" and k == math.floor(k) and k >= 1 then
        if k > maxi then
          maxi = k
        end
      else
        allint = false
      end
    end
    -- Dense integer keys are an array; sparse ones (quest IDs) are an object,
    -- because emitting a 25000-slot array of nulls would be absurd.
    if allint and n == maxi and n > 0 then
      local parts = {}
      for i = 1, n do
        parts[i] = encode(value[i])
      end
      return "[" .. table.concat(parts, ",") .. "]"
    end
    local keys = {}
    for k in pairs(value) do
      keys[#keys + 1] = k
    end
    -- Sort for deterministic output: byte-identical rebuilds are a requirement.
    table.sort(keys, function(a, b)
      if type(a) == type(b) then
        return a < b
      end
      return type(a) == "number"
    end)
    local parts = {}
    for _, k in ipairs(keys) do
      parts[#parts + 1] = encode(tostring(k)) .. ":" .. encode(value[k])
    end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  -- Functions and userdata are not data; drop them rather than fail, since
  -- upstream files legitimately contain helper functions.
  return "null"
end

return { encode = encode }
