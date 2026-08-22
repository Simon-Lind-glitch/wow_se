# WoW Classic Swedish translation addon — implementation spec

## 0. Resolved inputs

Answered by the requester **2026-08-22**. These are settled; do not re-ask. If
they change, change them here first — everything downstream reads from this
table.

| Input | Answer |
|---|---|
| Classic flavor + version | **TBC Anniversary** — Blizzard product `wow_anniversary`, **2.5.6 (build 69110)** |
| `## Interface` number | **20506** — from the client itself: `GetBuildInfo()` → `"2.5.6", "69110", 20506`, `WOW_PROJECT_ID = WOW_PROJECT_BURNING_CRUSADE_CLASSIC (5)` |
| Faction/race | **Horde, orc/troll** → phase 2 zone is **Durotar** |
| Reading age / English level | **~9**, dual-language **ON** by default |
| Translation backend | **None in the toolchain.** Translation happens outside it (in a Claude Code session, or by hand) and is imported through a validating offline path. Revised 2026-08-22: the requester has no API key, and the batch client was deleted rather than left unused. |

Consequences of the flavor answer, resolved once here so no stage has to guess:

- **Tooltip API (§7).** TBC Anniversary is a 2.5.x game build on the modern
  client engine, so it is *not* the 2021 TBC Classic API surface. Which of
  `GameTooltip:HookScript("OnTooltipSetItem")` and
  `TooltipDataProcessor.AddTooltipPostCall` exists cannot be established from
  outside the client, so `hooks/tooltip.lua` **feature-detects at load** and
  uses whichever is present. This is not hedging — it is the only correct
  answer when the addon must survive a client patch that swaps them.
- **Gossip API (§7).** Same treatment: prefer `C_GossipInfo.GetText()`, fall
  back to the global `GetGossipText()`.
- **Install path.** The Anniversary product does not install into
  `_classic_era_`. Confirm the actual folder on the game machine before copying
  (see README) — it is the one whose `WoW.exe` the Anniversary realms launch.

### Pinned upstream sources

Build-time only; never shipped. Pinned by commit SHA so a rebuild is
reproducible. Recorded in `tools/extract/sources.py`, which is the single place
they are defined.

| What | Source | Pin |
|---|---|---|
| `GlobalStrings` enUS (18,260 keys) | `Ketho/BlizzardInterfaceResources` @ `classic_anniversary`, `Resources/GlobalStrings/enUS.lua` | `d6d4a8f4` |
| Quest structure, zone assignment, objectives text | `Questie/Questie` @ `master`, `Database/TBC/tbcQuestDB.lua` | `4aea09ec` |
| Quest prose (description / progress / completion) | `cmangos/tbc-db` @ `master`, `Full_DB/TBCDB_*.sql.gz`, table `quest_template` | `da2de07e` |

**Correction to §6 as originally written.** The spec assumed Questie supplies
all five per-quest fields. It does not. Questie's `questKeys` carry `name` and
`objectivesText` (plus per-objective strings and `triggerEnd`) — there is no
description, progress, or completion prose anywhere in its database. Those three
come from the cmangos `quest_template` table (`Details`, `RequestItemsText`,
`OfferRewardText`), keyed by the same numeric quest ID Questie uses. Questie is
still the authority for *which* quests belong to Durotar. The original
instruction stands where it matters: quest text is not in the client on
Vanilla-lineage builds, so do not spend time on DB2/DBC.

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
- **Translate everything except names.** Revised 2026-08-22. Only the names of
  individual people, places and named organisations stay English (Gornek,
  Razor Hill, Burning Blade). Creature types, item names and class words are
  translated like any other noun.
  The original rule kept all of those English so the kids could follow guides,
  search Wowhead and talk to other players. That rationale is retired: the
  dual-language rendering puts the English original directly beneath the
  Swedish, so the lookup path already exists.
  Known rough edge: mob nameplates and bag item names come from the server and
  cannot be translated, so Swedish quest text will not match them word for
  word. The grey English line bridges that wherever it is on screen — the quest
  tracker, which has no room for two languages, is where to watch for trouble.
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

**Revised 2026-08-22 after in-game testing.** The original design — Swedish as
primary text with the English below in smaller grey type, default on — was
built, tried, and rejected by the requester: cluttered, hard to read, and it
doubled the height of every quest paragraph in a frame laid out for one
language. It is removed, not left behind a flag.

The intent it served is kept by two other means:

- **The English original on hover.** Pointing at translated text shows it in a
  tooltip. One gesture away instead of permanently in the way, and it depends
  on no frame's layout, which the inline version did.
- **Per-category switch back to English** (`/svse objective`, `/svse quest`, …).
  This is the path off the addon: turn off objectives once they can read them,
  then descriptions, category by category.

### Rendering the tokens

The client expands `$N`, `$B`, `$C`, `$R` and `$G` only in text it receives
from the server. Text an addon writes into a FontString is drawn literally, so
a translation carrying `$N` renders as those two characters in front of the
player, and `$B$B` collapses every paragraph break — which is exactly what
happened in the first build.

So the addon expands them itself at display time (`SVSE.Expand`). Format
specifiers (`%s`, `%d`) are deliberately left alone: those belong to whatever
Blizzard code owns the string and calls `format()` on it.

The stored translation keeps its tokens. Expansion is a property of rendering,
not of the data.

### GlobalStrings that are already on screen

§5's claim that reassigning the globals is enough holds only for strings the
client reads at the moment it uses them. Labels baked into a frame when
FrameXML built it — buttons, tab names — already hold the English, and
reassigning the global they came from does nothing. `hooks/frames.lua` re-applies
those after login from a small explicit table.

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
