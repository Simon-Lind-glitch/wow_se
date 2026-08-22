-- The addon's Normalize, checked against the shared vectors.
--
-- Runs under real Lua 5.1 because that is what the game runs. core.lua is
-- deliberately free of Blizzard API calls at load time, which is what makes
-- loading it here possible.

local function loadCore()
  local chunk = assert(loadfile("addon/WoWsvSE/core.lua"))
  local SVSE = {}
  chunk("WoWsvSE", SVSE)
  return SVSE
end

describe("SVSE.Normalize", function()
  local SVSE = loadCore()
  local vectors = assert(loadfile("tests/fixtures/normalize_vectors.lua"))()

  it("agrees with every shared vector", function()
    for index, case in ipairs(vectors) do
      local input, expected = case[1], case[2]
      assert.are.equal(expected, SVSE.Normalize(input), ("vector %d: %q"):format(index, input))
    end
  end)

  it("is idempotent", function()
    for _, case in ipairs(vectors) do
      local once = SVSE.Normalize(case[1])
      assert.are.equal(once, SVSE.Normalize(once))
    end
  end)

  it("returns empty string for non-strings", function()
    assert.are.equal("", SVSE.Normalize(nil))
    assert.are.equal("", SVSE.Normalize(42))
    assert.are.equal("", SVSE.Normalize({}))
  end)
end)
