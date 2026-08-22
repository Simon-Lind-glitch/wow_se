-- The build-time Lua bridge's JSON encoder (tools/common/lua/json.lua).
--
-- Run under real Lua 5.1 — the version the game runs — because that is where
-- the encoder has to be correct: it is what turns Questie's quest database and
-- the client's GlobalStrings into data Python can read. A quoting bug here
-- corrupts a handful of quests out of thousands and says nothing.

package.path = "tools/common/lua/?.lua;" .. package.path
local encode = require("json").encode

describe("json encoder", function()
  it("encodes plain strings", function()
    assert.are.equal('"hello"', encode("hello"))
  end)

  it("escapes quotes and backslashes", function()
    assert.are.equal('"he said \\"hi\\""', encode('he said "hi"'))
    assert.are.equal('"a\\\\b"', encode("a\\b"))
  end)

  it("escapes control characters", function()
    assert.are.equal('"a\\nb"', encode("a\nb"))
    assert.are.equal('"a\\tb"', encode("a\tb"))
    assert.are.equal('"a\\rb"', encode("a\rb"))
  end)

  it("passes UTF-8 through untouched", function()
    -- The sources are UTF-8 and the consumer decodes UTF-8; re-escaping these
    -- bytes would mangle å ä ö on the way back in.
    assert.are.equal('"Hana\'zua å ä ö"', encode("Hana'zua å ä ö"))
  end)

  it("encodes integers without a decimal point", function()
    assert.are.equal("788", encode(788))
    assert.are.equal("-61", encode(-61))
  end)

  it("encodes dense integer-keyed tables as arrays", function()
    assert.are.equal("[1,2,3]", encode({ 1, 2, 3 }))
  end)

  it("encodes sparse integer-keyed tables as objects", function()
    -- Questie's quest rows contain embedded nils, so this shape is normal.
    -- Emitting a 12515-slot array of nulls instead would be absurd.
    assert.are.equal('{"3":"c","10":"j"}', encode({ [3] = "c", [10] = "j" }))
  end)

  it("sorts object keys so rebuilds are byte-identical", function()
    -- Spec §9.3: a clean checkout must reproduce byte-identical output.
    assert.are.equal('{"a":1,"b":2,"c":3}', encode({ c = 3, a = 1, b = 2 }))
  end)

  it("encodes booleans and nested tables", function()
    assert.are.equal('{"nested":[1,{"k":true}]}', encode({ nested = { 1, { k = true } } }))
  end)

  it("drops functions rather than failing", function()
    -- Upstream files legitimately contain helper functions; they are not data.
    assert.are.equal('{"f":null}', encode({ f = function() end }))
  end)
end)
