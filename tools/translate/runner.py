"""Translate uncached strings and write them into the committed cache.

The invariants this stage enforces, in order of importance:

1. A translation whose placeholders do not round-trip is never written. It is
   retried, and if it still fails it is left untranslated — the addon renders
   the English (spec §7), which is the correct miss behaviour.
2. Nothing already cached is re-translated. Spec §6: re-runs cost nothing.
3. Cache writes happen after every round, so an interrupted run keeps the work
   it has paid for.
"""

from dataclasses import dataclass, field

from common import cache
from common.glossary import load as load_glossary
from common.hashkey import cache_key as cache_key_for
from common.mask import RoundTripError, mask, restore, validate
from common.paths import SOURCE, TRANSLATIONS
from translate import batch as batching
from translate.prompts import retry_message, system_prompt, user_message

CACHE_FILE = TRANSLATIONS / "sv.json"
REPORT_FILE = TRANSLATIONS / "report.json"

MAX_ITEMS_PER_REQUEST = 20
MAX_CHARS_PER_REQUEST = 6000


@dataclass
class Unit:
    """One string to translate, wherever it came from."""

    hash: str
    field: str
    en: str
    origin: str

    def to_item(self, index: int) -> dict:
        masked = mask(self.en)
        return {
            "i": index,
            "hash": self.hash,
            "field": self.field,
            "en": self.en,
            "origin": self.origin,
            "masked": masked.text,
            "masked_obj": masked,
            "gender_branches": [list(p) for p in masked.gender_branches],
        }


@dataclass
class Outcome:
    written: int = 0
    already_cached: int = 0
    rejected: dict[str, dict] = field(default_factory=dict)
    glossary_notes: dict[str, list[str]] = field(default_factory=dict)
    estimate: dict = field(default_factory=dict)


def load_units() -> list[Unit]:
    """Every translatable string in the source cache, deduplicated by hash."""
    units: dict[str, Unit] = {}

    ui = cache.read(SOURCE / "globalstrings.json", {})
    for key, entry in (ui.get("entries") or {}).items():
        units.setdefault(
            entry["hash"], Unit(entry["hash"], entry["field"], entry["en"], f"ui:{key}")
        )

    quests = cache.read(SOURCE / "quests_durotar.json", {})
    for quest_id, quest in (quests.get("quests") or {}).items():
        for name, entry in (quest.get("fields") or {}).items():
            units.setdefault(
                entry["hash"],
                Unit(entry["hash"], entry["field"], entry["en"], f"quest:{quest_id}.{name}"),
            )

    # Sorted so grouping — and therefore the batch itself — is reproducible.
    return sorted(units.values(), key=lambda u: (u.field, u.hash))


def select(units: list[Unit], cached: dict, *, model: str, remodel: bool) -> list[Unit]:
    pending = []
    for unit in units:
        entry = cached.get(unit.hash)
        if entry is None or (remodel and entry.get("model") != model):
            pending.append(unit)
    return pending


def build_groups(units: list[Unit]) -> list[batching.Group]:
    groups: list[batching.Group] = []
    by_field: dict[str, list[Unit]] = {}
    for unit in units:
        by_field.setdefault(unit.field, []).append(unit)

    for field_name in sorted(by_field):
        items = [u.to_item(0) for u in by_field[field_name]]
        for chunk_index, chunk in enumerate(
            batching.chunk(items, max_items=MAX_ITEMS_PER_REQUEST, max_chars=MAX_CHARS_PER_REQUEST)
        ):
            for position, item in enumerate(chunk, start=1):
                item["i"] = position
            groups.append(
                batching.Group(
                    custom_id=f"{field_name.replace('.', '-')}-{chunk_index:04d}",
                    field=field_name,
                    items=chunk,
                    system=system_prompt(field_name),
                    user=user_message(chunk),
                )
            )
    return groups


def _accept(item: dict, entry: dict, model: str, cached: dict, outcome: Outcome) -> bool:
    """Validate one translation and write it to the cache if it holds up."""
    swedish_masked = str(entry.get("sv", ""))
    problems = validate(item["masked_obj"], swedish_masked)
    if problems:
        outcome.rejected[item["hash"]] = {
            "origin": item["origin"],
            "en": item["en"],
            "attempt": swedish_masked,
            "problems": problems,
        }
        return False

    gender = entry.get("gender") or []
    pairs = [(str(p[0]), str(p[1])) for p in gender if isinstance(p, list) and len(p) == 2]
    try:
        swedish = restore(item["masked_obj"], swedish_masked, pairs)
    except RoundTripError as exc:
        outcome.rejected[item["hash"]] = {
            "origin": item["origin"],
            "en": item["en"],
            "attempt": swedish_masked,
            "problems": [str(exc)],
        }
        return False

    notes = load_glossary().violations(item["en"], swedish)
    if notes:
        outcome.glossary_notes[item["hash"]] = notes

    cached[item["hash"]] = {
        "sv": swedish,
        "en": item["en"],
        "field": item["field"],
        "model": model,
        "glossary_version": load_glossary().version,
        "tool_version": cache.TOOL_VERSION,
    }
    outcome.written += 1
    return True


def run(
    *,
    model: str = batching.DEFAULT_MODEL,
    limit: int | None = None,
    remodel: bool = False,
    dry_run: bool = False,
    retries: int = 1,
    log=print,
) -> Outcome:
    units = load_units()
    cached = cache.read(CACHE_FILE, {})
    outcome = Outcome(already_cached=sum(1 for u in units if u.hash in cached))

    pending = select(units, cached, model=model, remodel=remodel)
    if limit is not None:
        pending = pending[:limit]

    groups = build_groups(pending)
    outcome.estimate = batching.estimate_cost(groups, model)

    log(
        f"{len(units)} strings in source, {outcome.already_cached} already cached, "
        f"{len(pending)} to translate in {len(groups)} requests"
    )
    if not groups:
        return outcome
    log(
        f"estimate: ~{outcome.estimate['est_input_tokens']:,} in / "
        f"~{outcome.estimate['est_output_tokens']:,} out tokens, "
        f"~${outcome.estimate['est_usd']} on {model} (batch pricing)"
    )
    if dry_run:
        log("dry run: nothing submitted")
        return outcome

    batcher = batching.Batcher(model=model)
    replies = batcher.run(groups, on_status=log)

    retry_items: list[dict] = []
    for group in groups:
        reply = replies.get(group.custom_id)
        if reply is None:
            retry_items.extend(group.items)
            continue
        try:
            parsed = batching.parse_reply(reply)
        except batching.BatchError as exc:
            log(f"{group.custom_id}: {exc}")
            retry_items.extend(group.items)
            continue
        for item in group.items:
            entry = parsed.get(item["i"])
            if entry is None or not _accept(item, entry, model, cached, outcome):
                retry_items.append(item)

    cache.write(CACHE_FILE, cached)
    log(f"wrote {outcome.written} translations; {len(retry_items)} need a retry")

    # Retries go one at a time and synchronously: there are few of them, and the
    # prompt names the exact placeholder that was wrong last time.
    for attempt in range(retries):
        if not retry_items:
            break
        still_failing: list[dict] = []
        for item in retry_items:
            problems = outcome.rejected.get(item["hash"], {}).get("problems", ["no reply"])
            reply = batcher.translate_one(
                system_prompt(item["field"]),
                retry_message(item, problems),
                max_tokens=max(512, len(item["masked"]) * 2),
            )
            try:
                parsed = batching.parse_reply(reply)
            except batching.BatchError:
                still_failing.append(item)
                continue
            entry = parsed.get(item["i"])
            if entry and _accept(item, entry, model, cached, outcome):
                outcome.rejected.pop(item["hash"], None)
            else:
                still_failing.append(item)
        retry_items = still_failing
        cache.write(CACHE_FILE, cached)
        log(f"retry round {attempt + 1}: {len(retry_items)} still failing")

    cache.write(
        REPORT_FILE,
        {
            "model": model,
            "written": outcome.written,
            "rejected": outcome.rejected,
            "glossary_notes": outcome.glossary_notes,
            "estimate": outcome.estimate,
        },
    )
    if outcome.rejected:
        log(
            f"{len(outcome.rejected)} string(s) left untranslated after retries — "
            f"they render as English (spec §7). See {REPORT_FILE}"
        )
    if outcome.glossary_notes:
        log(f"{len(outcome.glossary_notes)} translation(s) disagree with the glossary; see report")
    return outcome


def export_pending(
    path,
    *,
    model: str = batching.DEFAULT_MODEL,
    limit: int | None = None,
    field: str | None = None,
    remodel: bool = False,
) -> int:
    """Write pending strings to a file for translation by something else.

    The escape hatch for every translator that is not the Batches API: a human,
    another tool, or an agent with no API key of its own. The file carries the
    masked text, so whoever fills it in sees the same [[0]] placeholders the
    model would, and the import path enforces the same round-trip rules.
    """
    units = load_units()
    cached = cache.read(CACHE_FILE, {})
    pending = select(units, cached, model=model, remodel=remodel)
    if field:
        # Prefix match on dotted segments, so `--field quest` selects every
        # quest.* field and `--field quest.objectives` selects just that one.
        pending = [u for u in pending if u.field == field or u.field.startswith(f"{field}.")]
    if limit is not None:
        pending = pending[:limit]

    items = []
    for index, unit in enumerate(pending, start=1):
        item = unit.to_item(index)
        entry = {
            "hash": item["hash"],
            "field": item["field"],
            "origin": item["origin"],
            "en": item["en"],
            "masked": item["masked"],
            "sv": "",
        }
        if item["gender_branches"]:
            entry["gender_branches"] = item["gender_branches"]
            entry["gender"] = []
        items.append(entry)

    cache.write(
        path,
        {
            "meta": {
                "note": (
                    "Fill in 'sv' for each item using the MASKED text: copy every [[n]] "
                    "placeholder exactly, once each, keeping non-positional ones in order. "
                    "For items with 'gender_branches', fill 'gender' with [male, female] "
                    "Swedish pairs. Then run: python -m translate --import-file <this file>"
                ),
                "count": len(items),
            },
            "items": items,
        },
    )
    return len(items)


def import_file(path, *, translator: str, log=print) -> Outcome:
    """Load translations from a file, validating exactly as the API path does.

    A translation that fails the placeholder round trip is rejected here too.
    Provenance is recorded under the translator's name so a later --remodel pass
    can find and upgrade it.
    """
    payload = cache.read(path, {})
    items = payload.get("items") or []
    cached = cache.read(CACHE_FILE, {})
    outcome = Outcome()
    skipped = 0

    for raw in items:
        swedish = str(raw.get("sv") or "").strip()
        if not swedish:
            skipped += 1
            continue
        english = raw["en"]
        item = {
            "i": 0,
            "hash": raw.get("hash") or cache_key_for(english, raw["field"]),
            "field": raw["field"],
            "en": english,
            "origin": raw.get("origin", "import"),
            "masked_obj": mask(english),
        }
        entry = {"sv": swedish}
        if raw.get("gender"):
            entry["gender"] = raw["gender"]
        _accept(item, entry, translator, cached, outcome)

    cache.write(CACHE_FILE, cached)
    log(
        f"imported {outcome.written} translation(s) from {path}; "
        f"{len(outcome.rejected)} rejected, {skipped} left blank"
    )
    # Always write the report: glossary disagreements are worth reading even
    # when every placeholder round-tripped.
    cache.write(
        REPORT_FILE,
        {
            "translator": translator,
            "written": outcome.written,
            "rejected": outcome.rejected,
            "glossary_notes": outcome.glossary_notes,
        },
    )
    for problem in list(outcome.rejected.values())[:5]:
        log(f"  rejected {problem['origin']}: {problem['problems']}")
    if outcome.glossary_notes:
        log(f"{len(outcome.glossary_notes)} translation(s) disagree with the glossary; see report")
    return outcome
