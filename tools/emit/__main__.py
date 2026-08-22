"""Stage 3 entry point: `python -m emit`.

Turns the committed caches into the Lua the addon ships:

    addon/WoWsvSE/WoWsvSE.toc
    addon/WoWsvSE/locale/globalstrings.lua
    addon/WoWsvSE/data/quests_durotar.lua

Offline and deterministic: same caches in, byte-identical files out (spec §9.3).
"""

import argparse
import sys

from common import cache
from common.normalize import normalize
from common.paths import ADDON, SOURCE
from emit import lua
from extract import sources
from translate import exchange

# Load order matters. core defines the namespace; the generated data files fill
# it; the hooks read it. globalstrings.lua only assigns Blizzard globals and
# depends on nothing.
TOC_FILES = (
    "core.lua",
    "render.lua",
    "locale/globalstrings.lua",
    "data/quests_durotar.lua",
    "hooks/quest.lua",
    "hooks/gossip.lua",
    "hooks/tooltip.lua",
    "hooks/frames.lua",
    "devtools/misslog.lua",
)

QUEST_FIELDS = ("title", "objectives", "description", "progress", "completion")


def write_toc(version: str, provenance: dict) -> int:
    lines = [
        f"## Interface: {provenance['interface']}",
        "## Title: WoWsvSE",
        "## Notes: Svensk text för gränssnitt och uppdrag.",
        "## Author: privat bygge",
        f"## Version: {version}",
        "## SavedVariables: WoWsvSEDB",
        "",
        f"# Generated for {provenance['flavor']} {provenance['game_version']} "
        f"({provenance['game_build']}) by emit {cache.TOOL_VERSION}.",
        "# Load order is significant — see tools/emit/__main__.py.",
        "",
        *TOC_FILES,
        "",
    ]
    path = ADDON / "WoWsvSE.toc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(TOC_FILES)


def write_globalstrings(entries: dict, provenance: dict) -> int:
    """Phase 1: plain global reassignment, alphabetized (spec §5)."""
    source = cache.read(SOURCE / "globalstrings.json").get("entries") or {}
    ui = entries.get("ui", {})

    body = []
    written = 0
    for key in sorted(source):
        swedish = ui.get(normalize(source[key]["en"]))
        if not swedish:
            continue  # untranslated: the client keeps its English (spec §7)
        body.append(f"{key} = {lua.quote(swedish['sv'])};")
        written += 1

    text = (
        lua.header(
            tool_version=cache.TOOL_VERSION,
            provenance=provenance,
            purpose=(
                "Swedish GlobalStrings. Assigning these replaces the client's own "
                "UI text at load; no hooking is involved (spec §5)."
            ),
        )
        + "\n".join(body)
        + "\n"
    )
    path = ADDON / "locale" / "globalstrings.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return written


def write_quests(entries: dict, provenance: dict) -> tuple[int, int]:
    """Phase 2: one table per quest, keyed by the numeric quest ID (spec §7)."""
    source = cache.read(SOURCE / "quests_durotar.json")
    quests = source.get("quests") or {}

    body = [
        "local _, SVSE = ...",
        "",
        "-- Keyed by numeric quest ID: stable, and preferred over a text hash",
        "-- wherever the game gives us one (spec §7).",
        "SVSE.quests = SVSE.quests or {}",
        "local q = SVSE.quests",
        "",
    ]
    quest_count = 0
    field_count = 0
    for quest_id in sorted(quests, key=int):
        fields = quests[quest_id].get("fields") or {}
        parts = []
        for name in QUEST_FIELDS:
            entry = fields.get(name)
            if not entry:
                continue
            swedish = entries.get(entry["field"], {}).get(normalize(entry["en"]))
            if not swedish:
                continue
            parts.append(f"{name} = {lua.quote(swedish['sv'])}")
            field_count += 1
        if not parts:
            continue
        quest_count += 1
        body.append(f"q[{int(quest_id)}] = {{")
        for part in parts:
            body.append(f"  {part},")
        body.append("}")

    text = (
        lua.header(
            tool_version=cache.TOOL_VERSION,
            provenance=provenance,
            purpose="Swedish quest text for Durotar, keyed by quest ID.",
        )
        + "\n".join(body)
        + "\n"
    )
    path = ADDON / "data" / "quests_durotar.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return quest_count, field_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emit", description=__doc__)
    parser.add_argument(
        "--version",
        default="0.1.0-dev",
        help="version stamped on the .toc (default: 0.1.0-dev)",
    )
    args = parser.parse_args(argv)

    provenance = sources.provenance()
    entries = exchange.load_translations()
    if not entries:
        print("nothing translated yet; run `make pending` first", file=sys.stderr)
        return 1

    files = write_toc(args.version, provenance)
    strings = write_globalstrings(entries, provenance)
    quests, fields = write_quests(entries, provenance)

    print(f"toc: {files} files, Interface {provenance['interface']}, version {args.version}")
    print(f"globalstrings.lua: {strings} strings")
    print(f"quests_durotar.lua: {quests} quests, {fields} fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
