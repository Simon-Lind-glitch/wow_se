"""The export/import round trip.

Translation happens outside the toolchain, so this is the only gate between a
translator and the addon. The property under test is that a translation whose
placeholders do not round-trip never reaches the cache — the addon's miss
behaviour is to render English (spec §7), which beats rendering a crash.
"""

import pytest

from common import cache
from translate import exchange


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(exchange, "CACHE_FILE", tmp_path / "sv.json")
    monkeypatch.setattr(exchange, "REPORT_FILE", tmp_path / "report.json")
    return tmp_path


def _units(*pairs):
    return [exchange.Unit("ui", en, f"ui:KEY_{i}") for i, en in enumerate(pairs)]


def _infile(tmp_path, *items):
    path = tmp_path / "in.json"
    cache.write(path, {"items": list(items)})
    return path


def item(en, sv, *, field="ui", origin="ui:K", **extra):
    return {"field": field, "origin": origin, "en": en, "sv": sv, **extra}


def test_key_is_the_normalized_english_not_a_hash():
    unit = exchange.Unit("ui", "  Quest   Log  ", "ui:QUEST_LOG")
    assert unit.key == "Quest Log"


def test_colour_codes_collapse_to_one_entry():
    plain = exchange.Unit("ui", "Quest Log", "ui:A")
    coloured = exchange.Unit("ui", "|cffffffffQuest Log|r", "ui:B")
    assert plain.key == coloured.key


def test_good_translation_is_stored_with_placeholders_restored(isolated):
    path = _infile(isolated, item("Kill %d boars", "Döda [[0]] vildsvin"))

    outcome = exchange.import_file(path, translator="tester", log=lambda *_: None)

    assert outcome.written == 1
    entries = exchange.load_translations()
    assert entries["ui"]["Kill %d boars"]["sv"] == "Döda %d vildsvin"
    assert entries["ui"]["Kill %d boars"]["by"] == "tester"


def test_dropped_placeholder_is_rejected(isolated):
    path = _infile(isolated, item("Give %s to %s", "Ge till", origin="ui:GIVE"))

    outcome = exchange.import_file(path, translator="tester", log=lambda *_: None)

    assert outcome.written == 0
    assert exchange.load_translations() == {}
    assert any("missing" in p for p in outcome.rejected["ui:GIVE"]["problems"])


def test_reordered_bare_specifier_is_rejected(isolated):
    path = _infile(isolated, item("Give %s to %s", "Ge [[1]] till [[0]]", origin="ui:GIVE"))

    outcome = exchange.import_file(path, translator="tester", log=lambda *_: None)

    assert outcome.written == 0
    assert any("reordered" in p for p in outcome.rejected["ui:GIVE"]["problems"])


def test_reordered_positional_specifier_is_allowed(isolated):
    # %1$s carries its own index, so Swedish word order may legitimately move it.
    path = _infile(isolated, item("You gain %1$s and %2$d", "Du får [[1]] och [[0]]"))

    assert exchange.import_file(path, translator="t", log=lambda *_: None).written == 1


def test_invented_placeholder_is_rejected(isolated):
    path = _infile(isolated, item("Kill %d boars", "Döda [[0]] och [[7]]", origin="ui:K"))

    outcome = exchange.import_file(path, translator="t", log=lambda *_: None)

    assert outcome.written == 0
    assert any("invented" in p for p in outcome.rejected["ui:K"]["problems"])


def test_gender_branches_are_recombined(isolated):
    path = _infile(
        isolated,
        item(
            "Greetings, $Glad:lass;!",
            "Hej, [[0]]!",
            gender_branches=[["lad", "lass"]],
            gender=[["pojke", "flicka"]],
        ),
    )

    exchange.import_file(path, translator="t", log=lambda *_: None)

    entries = exchange.load_translations()
    assert entries["ui"]["Greetings, $Glad:lass;!"]["sv"] == "Hej, $Gpojke:flicka;!"


def test_blank_is_not_done_yet_not_wrong(isolated):
    path = _infile(isolated, item("Accept", "   "))

    outcome = exchange.import_file(path, translator="t", log=lambda *_: None)

    assert (outcome.written, outcome.skipped_blank, outcome.rejected) == (0, 1, {})


def test_glossary_disagreements_are_advisory_not_fatal(isolated):
    path = _infile(isolated, item("Complete the quest", "Slutför grejen"))

    outcome = exchange.import_file(path, translator="t", log=lambda *_: None)

    assert outcome.written == 1  # stored anyway
    assert outcome.glossary_notes  # but flagged for a human


def test_export_then_import_round_trips(isolated, monkeypatch):
    monkeypatch.setattr(exchange, "load_units", lambda: _units("Kill %d boars"))
    path = isolated / "pending.json"

    assert exchange.export_pending(path) == 1
    payload = cache.read(path)
    assert payload["items"][0]["masked"] == "Kill [[0]] boars"
    assert payload["items"][0]["sv"] == ""

    payload["items"][0]["sv"] = "Döda [[0]] vildsvin"
    cache.write(path, payload)
    exchange.import_file(path, translator="t", log=lambda *_: None)

    assert exchange.load_translations()["ui"]["Kill %d boars"]["sv"] == "Döda %d vildsvin"


def test_export_excludes_what_is_already_translated(isolated, monkeypatch):
    monkeypatch.setattr(exchange, "load_units", lambda: _units("Accept", "Decline"))
    exchange.save_translations({"ui": {"Accept": {"sv": "Acceptera", "by": "t"}}})

    assert exchange.export_pending(isolated / "p.json") == 1
    assert cache.read(isolated / "p.json")["items"][0]["en"] == "Decline"


def test_export_can_be_restricted_to_a_field_prefix(isolated, monkeypatch):
    units = [
        exchange.Unit("ui", "Accept", "ui:ACCEPT"),
        exchange.Unit("quest.title", "Cutting Teeth", "quest:788.title"),
        exchange.Unit("quest.objectives", "Kill boars", "quest:788.objectives"),
    ]
    monkeypatch.setattr(exchange, "load_units", lambda: units)

    assert exchange.export_pending(isolated / "a.json", field_prefix="quest") == 2
    assert exchange.export_pending(isolated / "b.json", field_prefix="quest.title") == 1
