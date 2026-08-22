-- NPC gossip: the greeting text on the "what would you like to talk about"
-- window.
--
-- Two APIs exist depending on the build. TBC Anniversary is a 2.5.x game on the
-- modern client engine, so which one is present cannot be established from
-- outside the client (spec §0). Detect, do not assume.

local _, SVSE = ...

local function gossipText()
  if C_GossipInfo and C_GossipInfo.GetText then
    return C_GossipInfo.GetText()
  end
  if GetGossipText then
    return GetGossipText()
  end
  return nil
end

local function renderGossip()
  local frame = GossipGreetingText
  if not frame or not frame.SetText then
    return
  end
  local english = gossipText()
  if type(english) ~= "string" or english == "" then
    return
  end
  local rendered = SVSE.Render("gossip", english)
  if rendered and rendered ~= english then
    frame:SetText(rendered)
  end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("GOSSIP_SHOW")
frame:SetScript("OnEvent", renderGossip)
