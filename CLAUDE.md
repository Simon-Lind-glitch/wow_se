# WoW Classic Swedish translation addon

**Read `SPEC.md` first.** It is the authoritative spec and takes precedence over
anything inferred from the code. This file is only a pointer plus the rules that
are cheap to violate by accident.

## What this is

A private, offline-built addon rendering WoW Classic's UI and quest text in
Swedish for two child players. Not published. The addon ships **no translation
logic** — only generated lookup tables and a thin rendering layer. Translation
happens in `tools/`, on the dev machine, once per game patch.

## Before generating anything

Four inputs in `SPEC.md` §0 are still **unanswered**: Classic flavor+version,
faction/race, reading age, translation backend. The spec says ask, do not guess.
Flavor is load-bearing — it decides the `## Interface` number, the Questie DB
branch, and which tooltip API applies (§7). Ask the user rather than picking a
default.

## Never (SPEC.md §2, §3)

These are rejected designs, not gaps. `make guard` fails the build on most of
them; do not work around it.

- No `CHAT_MSG_*` event registration, ever. No `ChatFrame_AddMessageEventFilter`.
- No `io`, `os.execute`, `require`, sockets — Lua 5.1 sandbox.
- Never replace a Blizzard function outright. `hooksecurefunc` only: overwriting
  taints the execution path and breaks protected actions in combat.
- Never hand-edit generated files (`locale/globalstrings.lua`, `data/*.lua`).
  Fix the toolchain and regenerate.
- Don't modify strings other addons parse (combat log, item links, DBM triggers).
- No companion app, no runtime network access, no public release.

## Easy to get wrong

- **Format specifiers** (`%s`, `%1$s`) and **quest tokens** (`$N $B $C $R $G`)
  must round-trip exactly. A dropped or reordered specifier is a runtime error.
  Mask before translation, restore after; reject non-round-tripping output.
- **Miss behavior is render-the-English.** Never an error, never an empty
  string, never a block.
- **Proper nouns stay in English** — NPC, zone, item, spell, creature names.
- **`tools/cache/` is committed on purpose** (§9.3). Don't gitignore it.

## Environment

Devcontainer: Python 3.12 (toolchain) + Lua 5.1 (the game's VM). Lua 5.1 is a
real runtime here, not just for syntax — the extract stage loads Questie's DB
and `GlobalStrings.lua` as Lua data rather than regex-parsing them, and `busted`
tests the masking logic on the same VM version the game runs.

```
make help      # all targets
make all       # extract -> translate -> emit -> verify
make verify    # guard + lint + fmt-check + test
```

`make translate` needs `ANTHROPIC_API_KEY` from the host env; every other target
runs without it.

The `ai-skills` plugin is enabled at project scope via the committed
`.claude/settings.json`, and `.devcontainer/post-create.sh` clones the
marketplace into the container on create. If plugin skills seem missing, run
`claude plugin list` — then `bash .devcontainer/post-create.sh` to re-warm.
