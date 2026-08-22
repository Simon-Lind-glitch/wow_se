"""Assemble the Durotar quest corpus from Questie plus the cmangos world DB.

Questie decides *which* quests belong to the zone (`zoneOrSort`) and supplies
titles and quest-log objectives text. The cmangos `quest_template` table
supplies the three prose fields Questie has no column for. See the §6
correction in SPEC.md.
"""

from dataclasses import dataclass, field
from pathlib import Path

from common.luadata import LuaLoadError, load_questie
from extract import questtext, sources

# Durotar. Questie stores AreaTable IDs in `zoneOrSort`, and the zone's quests
# are split between Durotar proper (14) and the Valley of Trials (363) — the
# starting area every orc and troll passes through. Verified empirically against
# known quests (Lazy Peons, Cutting Teeth, Sarkoth) rather than assumed.
DUROTAR_AREAS = (14, 363)

# Positional index of the fields we read, from Questie's own `questKeys` table.
# Read from upstream at runtime rather than hardcoded, because the order shifts
# between Questie releases.
_WANTED_KEYS = ("name", "objectivesText", "zoneOrSort", "questLevel", "requiredRaces")

# Rows that exist in the database but never in a live game.
_JUNK_TITLE_PREFIXES = ("BETA", "[UNUSED]", "TEST", "[DEPRECATED]", "DEPRECATED")

# Translatable fields, in the order they matter. Objectives first: spec §6 says
# they are the priority because they are what unblocks play.
QUEST_FIELDS = ("objectives", "title", "description", "progress", "completion")


@dataclass
class Quest:
    id: int
    level: int
    title: str = ""
    objectives: str = ""
    description: str = ""
    progress: str = ""
    completion: str = ""
    sources: dict[str, str] = field(default_factory=dict)

    def translatable(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in QUEST_FIELDS if getattr(self, name).strip()}


def _cell(row: dict | list, index: int) -> object:
    """Read a 1-based Lua field out of a row that may be a list or a sparse map.

    Questie's rows contain embedded nils, so the Lua->JSON bridge emits some as
    arrays and some as objects keyed by stringified index. Both shapes are
    normal; treating only one as valid drops quests.
    """
    if isinstance(row, dict):
        return row.get(str(index))
    return row[index - 1] if 0 < index <= len(row) else None


def _questie_field_index(keys: dict[str, int]) -> dict[str, int]:
    missing = [name for name in _WANTED_KEYS if name not in keys]
    if missing:
        raise LuaLoadError(f"Questie questKeys is missing expected fields: {missing}")
    return {name: int(keys[name]) for name in _WANTED_KEYS}


def load(
    *,
    questie_db: Path,
    questie_keys: Path,
    world_db: Path,
    areas: tuple[int, ...] = DUROTAR_AREAS,
) -> list[Quest]:
    """Return the zone's quests with every translatable field populated."""
    keys = _questie_field_index(load_questie(questie_keys, "questKeys"))
    rows = load_questie(questie_db, "questData")

    in_zone: dict[int, dict] = {}
    for raw_id, row in rows.items():
        zone = _cell(row, keys["zoneOrSort"])
        if isinstance(zone, int) and zone in areas:
            in_zone[int(raw_id)] = row

    texts = questtext.load(world_db, wanted_ids=set(in_zone))

    quests: list[Quest] = []
    for quest_id, row in sorted(in_zone.items()):
        title = str(_cell(row, keys["name"]) or "")
        if title.startswith(_JUNK_TITLE_PREFIXES):
            continue
        prose = texts.get(quest_id)
        quest = Quest(
            id=quest_id,
            level=int(_cell(row, keys["questLevel"]) or 0),
            title=title,
        )
        if prose:
            quest.description = prose.description
            quest.progress = prose.progress
            quest.completion = prose.completion
            # Prefer the client's own objectives wording; fall back to
            # Questie's, which is community-edited and occasionally paraphrased.
            quest.objectives = prose.objectives or _joined_objectives(row, keys)
            quest.sources = {"prose": "cmangos", "objectives": "cmangos"}
        else:
            quest.objectives = _joined_objectives(row, keys)
            quest.sources = {"prose": "missing", "objectives": "questie"}
        quests.append(quest)
    return quests


def _joined_objectives(row: dict | list, keys: dict[str, int]) -> str:
    raw = _cell(row, keys["objectivesText"])
    if isinstance(raw, dict):
        parts = [raw[k] for k in sorted(raw, key=lambda x: int(x))]
    elif isinstance(raw, list):
        parts = raw
    else:
        return ""
    return "\n".join(str(p) for p in parts if p and str(p).strip())


def default_paths() -> dict[str, Path]:
    return {
        "questie_db": sources.QUESTIE_QUESTS.local,
        "questie_keys": sources.QUESTIE_KEYS.local,
        "world_db": sources.CMANGOS_DB.local,
    }
