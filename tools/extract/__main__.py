"""Stage 1 entry point: `python -m extract`.

Writes the committed source cache that translate and emit both read:

    tools/cache/source/globalstrings.json   keys this client renders
    tools/cache/source/globalstrings_review.json   flagged for a human (§5)
    tools/cache/source/quests_durotar.json  the zone corpus

Needs network on a cold cache; everything downstream does not.
"""

import argparse
import sys

from common import cache
from common.glossary import load as load_glossary
from common.luadata import load as load_lua
from common.mask import mask, round_trips
from common.paths import SOURCE, TRANSLATIONS, ensure_dirs
from extract import quests, sources
from extract.classify import Classifier, Verdict


def _unit(text: str, field: str) -> dict:
    """One translatable string plus everything translate needs to handle it."""
    masked = mask(text)
    return {
        "en": text,
        "field": field,
        "placeholders": len(masked.tokens),
        "gender_branches": [list(pair) for pair in masked.gender_branches],
    }


def extract_globalstrings(*, force: bool) -> tuple[int, int]:
    path = sources.fetch(sources.GLOBALSTRINGS, force=force)
    strings = load_lua(path)

    tarball = sources.DOWNLOADS / "ui_source.tar.gz"
    if not tarball.exists():
        sources.fetch(sources.UI_SOURCE_TARBALL, url=sources.UI_SOURCE_URL, force=force)
    # Existing translations are exempt from the scope filter (see classify.py).
    stored = cache.read(TRANSLATIONS / "sv.json", {}).get("entries") or {}
    # The cache is keyed by the normalized English, which is what we match on.
    translated = {key for field in stored.values() for key in field}
    classifier = Classifier(tarball, already_translated=translated)
    if not classifier.has_ui_source:
        print("warning: UI source unavailable; keeping every key that looks renderable")

    translate: dict[str, dict] = {}
    review: dict[str, dict] = {}
    skipped: dict[str, int] = {}
    rejected: dict[str, str] = {}

    for key in sorted(strings):
        value = strings[key]
        decision = classifier.classify(key, value)
        if decision.verdict is Verdict.SKIP:
            skipped[decision.reason] = skipped.get(decision.reason, 0) + 1
            continue
        if not round_trips(value):
            # Refuse to send anything we cannot put back together. Better a
            # missing translation (renders English, §7) than a broken one.
            rejected[key] = "placeholders do not round-trip"
            continue
        entry = _unit(value, field="ui")
        entry["reason"] = decision.reason
        (review if decision.verdict is Verdict.REVIEW else translate)[key] = entry

    meta = sources.provenance() | {
        "tool_version": cache.TOOL_VERSION,
        "glossary_version": load_glossary().version,
        "source_keys": len(strings),
        "translate": len(translate),
        "review": len(review),
        "rejected": len(rejected),
        "skipped_by_reason": skipped,
    }
    cache.write(SOURCE / "globalstrings.json", {"meta": meta, "entries": translate})
    cache.write(
        SOURCE / "globalstrings_review.json",
        {
            "meta": {
                "note": "Flagged by §5 as possibly parsed rather than rendered. "
                "Move an entry into globalstrings.json to translate it.",
                "rejected": rejected,
            },
            "entries": review,
        },
    )
    return len(translate), len(review)


def extract_quests(*, force: bool) -> tuple[int, int]:
    paths = quests.default_paths()
    for source in (sources.QUESTIE_QUESTS, sources.QUESTIE_KEYS, sources.CMANGOS_DB):
        sources.fetch(source, force=force)

    corpus = quests.load(**paths)
    out: dict[str, dict] = {}
    units = 0
    rejected: dict[str, str] = {}
    for quest in corpus:
        fields = {}
        for name, text in quest.translatable().items():
            if not round_trips(text):
                rejected[f"{quest.id}.{name}"] = "placeholders do not round-trip"
                continue
            fields[name] = _unit(text, field=f"quest.{name}")
            units += 1
        out[str(quest.id)] = {
            "level": quest.level,
            "title_en": quest.title,
            "sources": quest.sources,
            "fields": fields,
        }

    meta = sources.provenance() | {
        "tool_version": cache.TOOL_VERSION,
        "glossary_version": load_glossary().version,
        "zone": "Durotar",
        "areas": list(quests.DUROTAR_AREAS),
        "quests": len(out),
        "units": units,
        "rejected": rejected,
    }
    cache.write(SOURCE / "quests_durotar.json", {"meta": meta, "quests": out})
    return len(out), units


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="extract", description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download pinned sources")
    parser.add_argument(
        "--only",
        choices=("globalstrings", "quests"),
        help="run a single phase instead of both",
    )
    args = parser.parse_args(argv)
    ensure_dirs()

    if args.only != "quests":
        translate, review = extract_globalstrings(force=args.force)
        print(f"globalstrings: {translate} to translate, {review} flagged for review")
    if args.only != "globalstrings":
        count, units = extract_quests(force=args.force)
        print(f"quests: {count} Durotar quests, {units} translatable fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
