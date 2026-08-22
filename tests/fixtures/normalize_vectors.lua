-- Shared normalization vectors.
--
-- Read by BOTH tests/normalize_spec.lua (Lua 5.1, the addon's implementation)
-- and tools/tests/test_normalize.py (Python, the toolchain's). The two
-- implementations must agree exactly or every lookup in the game misses, so
-- they are checked against one list rather than two copies that drift.

return {
  { "Quest Log", "Quest Log" },
  { "  leading and trailing  ", "leading and trailing" },
  { "collapse   inner    spaces", "collapse inner spaces" },
  { "tabs\tand\nnewlines", "tabs and newlines" },
  { "", "" },
  -- Colour codes are presentation: the same sentence in two colours must not
  -- become two cache entries (spec §7).
  { "|cff00ff00Green text|r", "Green text" },
  { "|cffff0000Red|r and |cff00ff00green|r", "Red and green" },
  -- A hyperlink keeps its display text and loses its payload.
  { "|Hquest:123:60|h[Lazy Peons]|h needs you", "[Lazy Peons] needs you" },
  -- Inline textures carry no text at all.
  { "|TInterface\\Icons\\Spell_Fire:16|t Fire", "Fire" },
  -- Format specifiers and quest tokens are content, not presentation: they
  -- must survive normalization untouched.
  { 'Abandon "%s"?', 'Abandon "%s"?' },
  { "Hello $N, brave $C.$B$BGo.", "Hello $N, brave $C.$B$BGo." },
  { "You gain %1$s and %2$d", "You gain %1$s and %2$d" },
  { "Greetings, $Glad:lass;!", "Greetings, $Glad:lass;!" },
  -- Swedish output round-trips too; å ä ö are ordinary characters here.
  { "  Döda 10 fläckiga vildsvin  ", "Döda 10 fläckiga vildsvin" },
  { "|cff808080Kill 10 Mottled Boars|r", "Kill 10 Mottled Boars" },
}
