"""Move strings out for translation and back in, validated.

Translation happens outside this toolchain — in a Claude Code session, by hand,
or in any other tool. This module is the whole interface: it writes out what
still needs translating, and reads back what came in, refusing anything whose
placeholders do not survive the round trip.

That refusal is the only reason this layer exists. Everything else here is
bookkeeping.
"""

from dataclasses import dataclass, field

from common import cache
from common.glossary import load as load_glossary
from common.mask import RoundTripError, mask, restore, validate
from common.normalize import normalize
from common.paths import SOURCE, TRANSLATIONS

CACHE_FILE = TRANSLATIONS / "sv.json"
REPORT_FILE = TRANSLATIONS / "report.json"


@dataclass(frozen=True)
class Unit:
    """One string to translate, wherever it came from."""

    field: str
    en: str
    origin: str

    @property
    def key(self) -> str:
        """Lookup key: the normalized English.

        Not a hash. The same sentence in two colours must share one entry, and
        normalizing gets that; hashing it too only made the cache unreadable in
        a diff. Entries are grouped by field, so a quest title and a UI label
        that happen to share wording still get their own translation.
        """
        return normalize(self.en)


@dataclass
class Outcome:
    written: int = 0
    rejected: dict[str, dict] = field(default_factory=dict)
    glossary_notes: dict[str, list[str]] = field(default_factory=dict)
    skipped_blank: int = 0


def load_units() -> list[Unit]:
    """Every translatable string in the source cache, deduplicated."""
    units: dict[tuple[str, str], Unit] = {}

    ui = cache.read(SOURCE / "globalstrings.json", {})
    for name, entry in (ui.get("entries") or {}).items():
        unit = Unit(entry["field"], entry["en"], f"ui:{name}")
        units.setdefault((unit.field, unit.key), unit)

    quests = cache.read(SOURCE / "quests_durotar.json", {})
    for quest_id, quest in (quests.get("quests") or {}).items():
        for name, entry in (quest.get("fields") or {}).items():
            unit = Unit(entry["field"], entry["en"], f"quest:{quest_id}.{name}")
            units.setdefault((unit.field, unit.key), unit)

    return sorted(units.values(), key=lambda u: (u.field, u.key))


def load_translations() -> dict:
    """The translation cache, as {field: {normalized_en: {...}}}."""
    return cache.read(CACHE_FILE, {}).get("entries") or {}


def save_translations(entries: dict) -> None:
    cache.write(
        CACHE_FILE,
        {
            "meta": {
                "tool_version": cache.TOOL_VERSION,
                "glossary_version": load_glossary().version,
                "count": sum(len(v) for v in entries.values()),
            },
            "entries": entries,
        },
    )


def pending(units: list[Unit], entries: dict, *, field_prefix: str | None = None) -> list[Unit]:
    out = []
    for unit in units:
        if field_prefix and not (
            unit.field == field_prefix or unit.field.startswith(f"{field_prefix}.")
        ):
            continue
        if unit.key not in entries.get(unit.field, {}):
            out.append(unit)
    return out


def export_pending(
    path,
    *,
    limit: int | None = None,
    field_prefix: str | None = None,
    redo: bool = False,
) -> int:
    """Write untranslated strings to a file for whoever is translating.

    With `redo`, already-translated strings are included too, each carrying its
    current translation as `previous` for reference. Needed whenever a policy
    changes under text that was already done — the glossary is not versioned
    per entry, so the alternative is hand-picking strings out of the cache.
    """
    entries = load_translations()
    units = load_units()
    if redo:
        todo = [
            u
            for u in units
            if not field_prefix or u.field == field_prefix or u.field.startswith(f"{field_prefix}.")
        ]
    else:
        todo = pending(units, entries, field_prefix=field_prefix)
    if limit is not None:
        todo = todo[:limit]

    items = []
    for unit in todo:
        masked = mask(unit.en)
        item = {
            "field": unit.field,
            "origin": unit.origin,
            "en": unit.en,
            "masked": masked.text,
            "sv": "",
        }
        if masked.gender_branches:
            item["gender_branches"] = [list(p) for p in masked.gender_branches]
            item["gender"] = []
        existing = entries.get(unit.field, {}).get(unit.key)
        if redo and existing:
            item["previous"] = existing["sv"]
        items.append(item)

    cache.write(
        path,
        {
            "meta": {
                "note": (
                    "Fill in 'sv' for each item using the MASKED text: copy every [[n]] "
                    "placeholder exactly, once each, keeping non-positional ones in order. "
                    "Then: python -m translate --import-file <this file>"
                ),
                "count": len(items),
            },
            "items": items,
        },
    )
    return len(items)


def import_file(path, *, translator: str, log=print) -> Outcome:
    """Read translations back, rejecting any that break their placeholders."""
    items = cache.read(path, {}).get("items") or []
    entries = load_translations()
    glossary = load_glossary()
    outcome = Outcome()

    for raw in items:
        swedish_masked = str(raw.get("sv") or "").strip()
        if not swedish_masked:
            outcome.skipped_blank += 1
            continue

        english = raw["en"]
        field_name = raw["field"]
        origin = raw.get("origin", "import")
        masked = mask(english)

        problems = validate(masked, swedish_masked)
        if problems:
            outcome.rejected[origin] = {
                "en": english,
                "attempt": swedish_masked,
                "problems": problems,
            }
            continue

        pairs = [
            (str(p[0]), str(p[1]))
            for p in (raw.get("gender") or [])
            if isinstance(p, list) and len(p) == 2
        ]
        try:
            swedish = restore(masked, swedish_masked, pairs)
        except RoundTripError as exc:
            outcome.rejected[origin] = {
                "en": english,
                "attempt": swedish_masked,
                "problems": [str(exc)],
            }
            continue

        notes = glossary.violations(english, swedish)
        if notes:
            outcome.glossary_notes[origin] = notes

        entries.setdefault(field_name, {})[normalize(english)] = {"sv": swedish, "by": translator}
        outcome.written += 1

    save_translations(entries)
    cache.write(
        REPORT_FILE,
        {
            "translator": translator,
            "written": outcome.written,
            "rejected": outcome.rejected,
            "glossary_notes": outcome.glossary_notes,
        },
    )
    log(
        f"imported {outcome.written}; {len(outcome.rejected)} rejected, "
        f"{outcome.skipped_blank} left blank"
    )
    for origin, problem in list(outcome.rejected.items())[:5]:
        log(f"  rejected {origin}: {problem['problems']}")
    if outcome.glossary_notes:
        log(f"{len(outcome.glossary_notes)} disagree with the glossary; see {REPORT_FILE.name}")
    return outcome
