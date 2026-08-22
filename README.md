# WoW Classic Swedish translation addon (`WoWsvSE`)

Private, offline-built addon that renders WoW Classic's UI and quest text in
Swedish for two child players. The addon ships **no translation logic** — only
generated lookup tables plus a thin rendering layer. All translation happens in
this repo's toolchain, on the developer's machine, once per game patch.

The authoritative spec is [`SPEC.md`](SPEC.md) — read it before changing
anything. In particular §2 (non-goals) lists designs that were considered and
rejected; `make guard` enforces them. `CLAUDE.md` is a short pointer to the spec
for agents working in the container.

---

## Status

**Devcontainer only.** The toolchain (`tools/extract`, `tools/translate`,
`tools/emit`) and the addon itself are not written yet. The `make` targets are
wired up and will fail until their modules exist.

### Settled (spec §0)

| Input | Answer |
|---|---|
| Classic flavor + version | TBC Anniversary **2.5.6** (build 69110), `## Interface: 20506` |
| Faction/race | Horde, orc/troll → phase 2 is **Durotar** |
| Reading age | ~9, dual-language on |
| Translation backend | **none in the toolchain** — see below |

Tooltips and gossip are feature-detected at load rather than pinned to one API,
because a 2.5.x game build on the modern client engine may expose either
`OnTooltipSetItem` or `TooltipDataProcessor.AddTooltipPostCall`.

---

## Getting started

### Prerequisites (Windows + WSL2)

1. Docker Desktop installed, **and** WSL integration enabled for this distro
   (`Ubuntu-26.04`): Docker Desktop → Settings → Resources → WSL Integration.
2. Your user in the `docker` group. If `docker version` says *permission denied*
   on `/var/run/docker.sock` even though `id -nG <user>` lists `docker`, your
   shell session predates the group change. Fix it from **Windows**:
   ```powershell
   wsl --shutdown
   ```
   then reopen the terminal. `id -nG` (no username) must now include `docker`.
3. VS Code with the **Dev Containers** extension.

### Open it

```bash
code /home/simon/git/wow_swe
```

Then *Dev Containers: Reopen in Container*. No API key is needed — the whole
pipeline runs offline.

### What's in the container

| Tool | Why |
|---|---|
| Python 3.12 | extract, glossary, emit |
| Lua **5.1** | the exact VM the game runs |
| `luacheck` | addon linting against a WoW global allowlist (`.luacheckrc`) |
| `stylua` | addon formatting, `syntax = "Lua51"` |
| `busted` | unit tests for masking / placeholder round-trip |
| `ruff`, `pytest` | toolchain lint and tests |
| `claude` | the agent works in here, so the CLI ships in the image |

Lua 5.1 is in the image for two reasons beyond editing: Questie's quest DB and
the client's `GlobalStrings.lua` are both Lua source, so the extract stage
*loads* them in a sandboxed interpreter rather than regex-parsing them — and the
placeholder-masking logic gets tested on the same VM version that will run it.

### Agent plugins

The `ai-skills` plugin is wired up at **project scope**, so any agent working in
this repo gets it without manual setup. Two pieces make that work:

- `.claude/settings.json` (**committed**) declares the marketplace and enables
  the plugin. This travels with the repo.
- `$HOME/.claude/plugins/` holds the actual marketplace clone. This is
  container-local and does *not* travel, so `post-create.sh` re-materializes it
  on first create. It's public-repo git cloning — no credentials needed.

`~/.claude` is a **named Docker volume** (`wow-swe-claude-home`), deliberately
not a bind to the host's `~/.claude`. So container logins and plugin state
persist across rebuilds without the container inheriting host user-scope
settings. Log in once with `claude`; it sticks.

To add another plugin, install it at project scope so it's committed rather than
living only on your machine:

```bash
claude plugin marketplace add <owner>/<repo> --scope project
claude plugin install <plugin>@<marketplace> --scope project
```

Then add the same pair to `.devcontainer/post-create.sh` so fresh containers
warm it too.

---

## Build pipeline

```
make all       # extract -> emit -> verify
make verify    # guard + lint + fmt-check + test
make translate # how much is translated so far
make help      # all targets
```

### How translation works

There is no LLM SDK in this repo and no API key anywhere. Translation happens
*outside* the toolchain; the toolchain only lets strings in and out:

```
make pending              # writes strings.json — everything not yet translated
                          #   FIELD=quest LIMIT=50 to narrow it
<translate strings.json>  # in a Claude Code session, by hand, any tool
make import BY="whoever"  # reads it back
```

`make import` is the gate. It re-masks each English source, checks that every
`%s`, `%d`, `$N` and `$B` survived the round trip, and **refuses** anything that
did not. A rejected string stays untranslated, so the addon renders English
(§7) rather than something that errors in a child's game. Rejections and
glossary disagreements land in `tools/cache/translations/report.json`.

`make guard` fails the build if the addon tree contains `CHAT_MSG_*`,
`ChatFrame_AddMessageEventFilter`, `io.*`, `os.execute`, `require`, or an
outright assignment over a Blizzard function. These are the §2/§3 rules that
carry real consequences — account actioning, or tainting the execution path and
breaking protected actions in combat.

`tools/cache/` is **committed on purpose** (§9.3): a clean checkout must
reproduce byte-identical output without spending a single API call.

### Getting the source strings

`GlobalStrings.lua` is not a loose file in a modern client — it lives inside the
CASC archive. Practical routes, in order of preference:

1. A FrameXML dump repo for the target flavor (no client needed, easy to pin to
   a build number). This is what the extract stage should default to.
2. `wago.tools` export.
3. Local extraction with CascView, then mount the output read-only — there's a
   commented `mounts` entry in `devcontainer.json` for this.

Quest text is **not** in the client on Vanilla-lineage builds. It comes from
Questie. Do not spend time on DB2/DBC.

---

## Deploying to the game machine

The container can't write to the WoW install (it's on the Windows host, and the
addon must land on whatever machine the kids play on). Copy the tree by hand:

```
addon/WoWsvSE/  ->  <WoW>/_classic_era_/Interface/AddOns/WoWsvSE/
```

Then `/console scriptErrors 1` in-game and check every default panel (§5
acceptance). Between sessions, pull the dev-only miss log out of
SavedVariables to find gaps for the next build — it's behind a debug flag and
off by default, and the kids should never see any sign of it.
