# WoW Classic Swedish translation addon — implementation spec

## 0. Resolve these before writing code

Ask the requester; do not guess. Everything downstream depends on them.

| Input | Why it matters | Default if unanswered |
|---|---|---|
| Classic flavor + version (Era / Anniversary / MoP Classic / other) | Determines API surface, `## Interface` number, and which Questie DB branch to pull | Classic Era, latest |
| Faction/race the kids are playing | Decides whether phase 2 is Elwynn Forest or Durotar | Build both |
| Reading age / English level | Decides translation register and whether dual-language is default-on | Age 9, dual-language ON |
| Translation backend (API vs local model) | Cost and toolchain shape | Anthropic API, batch |

## 1. Goal

A **static, offline-built** addon that renders WoW Classic's interface and quest
text in Swedish for two child players. Private use. Not published.

The addon contains no translation logic. It contains generated lookup tables and
a thin rendering layer. All translation happens in a build toolchain on the
developer's machine, once per game patch.

## 2. Non-goals — do not build these

These were considered and explicitly rejected. Do not reintroduce them.

- **No chat translation.** Never register any `CHAT_MSG_*` event. Never call
  `ChatFrame_AddMessageEventFilter`. If these strings do not appear in the
  codebase, player-typed text cannot reach the addon.
- **No runtime network access.** WoW's Lua sandbox has none. Any design that
  implies fetching a translation during play is invalid.
- **No companion app, no watcher process, no API key on the user's machine.**
- **No memory reading or input automation.** Bannable.
- **No public release**, no CurseForge packaging, no localization framework for
  other target languages.

## 3. Hard constraints

- Lua 5.1 sandbox. No sockets, no `io`, no `os.execute`, no `require`.
- Use `hooksecurefunc` for Blizzard functions. Never replace one outright —
  that taints the execution path and breaks protected actions in combat.
- Do not modify strings other addons parse (combat log, item links, DBM triggers).
- Swedish is Latin-1; the client fonts have å/ä/ö. No custom font shipping needed.

## 4. Repository layout

```
/tools/                    # build-time only, never shipped
  extract/                 # pull source strings from client + Questie
  translate/               # batch translation, caching, retry
  emit/                    # write Lua tables
  glossary.sv.yaml         # locked term translations
  cache/                   # hash -> translation, committed to git
/addon/WoWsvSE/
  WoWsvSE.toc
  core.lua                 # lookup, settings, slash commands
  render.lua               # dual-language composition
  hooks/quest.lua
  hooks/gossip.lua
  hooks/tooltip.lua
  locale/globalstrings.lua # generated
  data/quests_elwynn.lua   # generated, one file per zone
  devtools/misslog.lua     # loaded only when a debug flag is set
```

Generated files carry a header comment naming the tool version and source build.
Never hand-edit them; fix the toolchain and regenerate.

## 5. Phase 1 — GlobalStrings (ship this first)

**Highest value per unit of work. Complete and verify before starting phase 2.**

Source: the client's `GlobalStrings.lua` for enUS. A few thousand short UI
strings — button labels, tab names, error messages, tooltip chrome.

These are plain Lua globals. **No hooking required.** Reassign at load:

```lua
QUEST_LOG = "Uppdragslogg"
INVENTORY_FULL = "Din väska är full"
```

Requirements:
- Preserve every format specifier exactly: `%s`, `%d`, `%1$s`, `%2$d`.
  A dropped or reordered specifier is a runtime error, not a typo.
- Translate only keys that render as user-visible text. Skip keys used as
  pattern templates for parsing (anything matched with `string.find` by
  convention — flag ambiguous cases for human review rather than guessing).
- Emit as a single flat file, alphabetized by key, for greppability.

**Acceptance:** log in, open every default UI panel (character, spellbook,
talents, quest log, bags, map, social, options). All chrome is Swedish. No Lua
errors with `/console scriptErrors 1`. No `?` or missing-glyph boxes.

## 6. Phase 2 — Quest text, one zone

Scope: **Elwynn Forest only** (or Durotar), ~150–200 quests. Do not attempt
full-corpus coverage.

Source: Questie's quest database for the target Classic flavor. Quest text is
**not** in the client on Vanilla-lineage builds — do not waste time trying to
extract it from DB2/DBC.

Per quest, translate: title, objectives, description, progress text, completion
text. Objectives are the priority — they are what unblocks play.

### Placeholder masking (critical)

Quest text contains inline tokens. Mask before translation, restore after.
Any output where the token set does not round-trip is a hard failure — reject
and retry, do not ship it.

| Token | Meaning |
|---|---|
| `$N` | player name |
| `$B` | line break |
| `$C` | class |
| `$R` | race |
| `$G male:female;` | gender-conditional text |

`$G` needs care: the two branches must both be translated, and Swedish
adjective agreement may differ from English. Handle it as structured data, not
as a string to be passed through wholesale.

### Translation rules

Pass these to the model as system-level instruction, not as a suffix:

- Target reader: a Swedish child, roughly age 9. Short sentences, everyday
  vocabulary. Prefer clarity over literary fidelity.
- Tone: adventurous, warm. This is a game, not a manual.
- **Keep proper nouns in English**: NPC names, zone names, item names, spell
  names, creature names. Rationale: the kids can still follow guides, look
  things up, and communicate with other players — and it sidesteps Swedish
  compound-noun and adjective-agreement problems.
- Apply `glossary.sv.yaml` for recurring game terms. Consistency across quests
  matters more than any individual best rendering.
- Preserve paragraph structure and `$B` breaks.

Cache by hash of the normalized source string so re-runs cost nothing. Commit
the cache.

**Acceptance:** a Swedish-reading adult reads all quests in the zone and finds
no line that would confuse a child. Placeholder round-trip is verified
programmatically for 100% of entries. Play the zone from level 1 to zone
completion with zero Lua errors.

## 7. Addon runtime

### Lookup

Key on a hash of the **normalized** source string: trim, collapse whitespace,
strip `|cffxxxxxx` color codes and `|H...|h` hyperlinks — then reapply them to
the output. Otherwise the same sentence in two colors becomes two entries.

Where a stable numeric quest ID is available, prefer it over the text hash.

Miss behavior: render the original English unchanged. Never render an error,
never render an empty string, never block.

### Hooks

- Quests: events `QUEST_DETAIL`, `QUEST_PROGRESS`, `QUEST_COMPLETE`. Read via
  `GetQuestText()`, `GetObjectiveText()`, `GetRewardText()`; write to
  `QuestInfoDescriptionText` and siblings. Quest log via `GetQuestLogQuestText()`.
- Gossip: `GOSSIP_SHOW` → `C_GossipInfo.GetText()` and the option list.
- Tooltips: `GameTooltip:HookScript("OnTooltipSetItem")` on older builds,
  `TooltipDataProcessor.AddTooltipPostCall` on newer. Verify which applies to
  the target version before writing.

Tag every string with its origin (`quest`, `gossip`, `tooltip`, `objective`).
Allowlist by origin — untagged strings are rendered as-is. Fail closed.

### Dual-language rendering

Default ON. Swedish as primary text, English below in smaller grey type
(`|cff808080`, ~85% size). Toggleable per-category via `/svse`.

This makes the addon a reading aid rather than a crutch, and gives the kids a
path off it. Support a per-zone toggle so it can be faded out as they improve.

### Dev-only miss logger

Behind a debug flag, off by default. Records any origin-tagged string rendered
without a translation to SavedVariables. The developer reads this file between
sessions to find gaps for the next build. **This is a build tool, not a user
feature** — no UI, no prompts, nothing the kids will see.

## 8. Phase 3 — expansion (do not start until phase 2 is in use)

Add zones one at a time, staying ahead of where the kids have leveled. Reuse
the toolchain unchanged; each zone is a data file, not a code change.

Add `LoadOnDemand` sharding only once resident memory becomes a measured
problem. Do not build it preemptively.

## 9. Definition of done for the engagement

1. Phase 1 shipped and verified.
2. Phase 2 shipped and verified for one zone.
3. Toolchain runs end-to-end from a clean checkout with one command, documented
   in a README, producing byte-identical output from the committed cache.
4. A short runbook for adding the next zone, written for the requester (a
   parent, not a full-time WoW addon developer).
