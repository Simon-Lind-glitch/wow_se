"""End-to-end translate flow with a stubbed model.

The property under test is the one that matters: a translation whose
placeholders do not round-trip must never reach the cache. The addon's miss
behaviour is to render English (spec §7), which is strictly better than
rendering something that crashes.
"""

import json

import pytest

from common import cache
from translate import batch as batching
from translate import runner


class FakeBatcher:
    """Stands in for the Batches API. Records what it was asked to do."""

    def __init__(self, group_replies, retry_replies=None, **_):
        self.group_replies = group_replies
        self.retry_replies = list(retry_replies or [])
        self.retry_calls = 0

    def run(self, groups, on_status=None):
        self.groups = groups
        return {g.custom_id: self.group_replies for g in groups}

    def translate_one(self, system, user, max_tokens=2048):
        self.retry_calls += 1
        if self.retry_replies:
            return self.retry_replies.pop(0)
        return json.dumps({"translations": [{"i": 1, "sv": "oanvändbar"}]})


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "CACHE_FILE", tmp_path / "sv.json")
    monkeypatch.setattr(runner, "REPORT_FILE", tmp_path / "report.json")
    return tmp_path


def _units(*pairs):
    return [
        runner.Unit(hash=f"h{i}", field="ui", en=en, origin=f"ui:KEY_{i}")
        for i, en in enumerate(pairs)
    ]


def _install(monkeypatch, units, replies, retries=None):
    monkeypatch.setattr(runner, "load_units", lambda: units)
    fake = FakeBatcher(replies, retries)
    monkeypatch.setattr(batching, "Batcher", lambda **kw: fake)
    return fake


def test_good_translation_is_cached_with_placeholders_restored(isolated, monkeypatch):
    units = _units("Kill %d boars")
    reply = json.dumps({"translations": [{"i": 1, "sv": "Döda [[0]] vildsvin"}]})
    _install(monkeypatch, units, reply)

    outcome = runner.run(log=lambda *_: None)

    assert outcome.written == 1
    stored = cache.read(runner.CACHE_FILE)
    assert stored["h0"]["sv"] == "Döda %d vildsvin"
    assert stored["h0"]["model"] == batching.DEFAULT_MODEL


def test_dropped_placeholder_is_never_cached_and_is_retried(isolated, monkeypatch):
    units = _units("Kill %d boars")
    bad = json.dumps({"translations": [{"i": 1, "sv": "Döda vildsvin"}]})
    good = json.dumps({"translations": [{"i": 1, "sv": "Döda [[0]] vildsvin"}]})
    fake = _install(monkeypatch, units, bad, retries=[good])

    outcome = runner.run(log=lambda *_: None)

    assert fake.retry_calls == 1
    assert outcome.written == 1
    assert cache.read(runner.CACHE_FILE)["h0"]["sv"] == "Döda %d vildsvin"
    assert outcome.rejected == {}


def test_persistently_bad_translation_is_left_untranslated(isolated, monkeypatch):
    units = _units("Kill %d boars")
    bad = json.dumps({"translations": [{"i": 1, "sv": "Döda vildsvin"}]})
    _install(monkeypatch, units, bad, retries=[bad])

    outcome = runner.run(log=lambda *_: None)

    assert outcome.written == 0
    assert "h0" not in cache.read(runner.CACHE_FILE)
    assert "h0" in outcome.rejected
    report = cache.read(runner.REPORT_FILE)
    assert "h0" in report["rejected"]
    assert any("missing" in p for p in report["rejected"]["h0"]["problems"])


def test_reordered_bare_specifier_is_rejected_end_to_end(isolated, monkeypatch):
    units = _units("Give %s to %s")
    swapped = json.dumps({"translations": [{"i": 1, "sv": "Ge [[1]] till [[0]]"}]})
    _install(monkeypatch, units, swapped, retries=[swapped])

    outcome = runner.run(log=lambda *_: None)

    assert outcome.written == 0
    assert any("reordered" in p for p in outcome.rejected["h0"]["problems"])


def test_cached_strings_are_not_resent(isolated, monkeypatch):
    units = _units("Kill %d boars")
    cache.write(
        runner.CACHE_FILE,
        {"h0": {"sv": "Döda %d vildsvin", "en": "Kill %d boars", "model": "x"}},
    )
    fake = _install(monkeypatch, units, "{}")

    outcome = runner.run(log=lambda *_: None)

    assert outcome.already_cached == 1
    assert outcome.written == 0
    assert not hasattr(fake, "groups")  # nothing was ever submitted


def test_remodel_resends_strings_from_a_different_model(isolated, monkeypatch):
    units = _units("Kill %d boars")
    cache.write(runner.CACHE_FILE, {"h0": {"sv": "gammal", "en": "Kill %d boars", "model": "old"}})
    good = json.dumps({"translations": [{"i": 1, "sv": "Döda [[0]] vildsvin"}]})
    _install(monkeypatch, units, good)

    outcome = runner.run(remodel=True, log=lambda *_: None)

    assert outcome.written == 1
    assert cache.read(runner.CACHE_FILE)["h0"]["sv"] == "Döda %d vildsvin"


def test_dry_run_submits_nothing_but_reports_cost(isolated, monkeypatch):
    units = _units("Kill %d boars", "Accept")
    fake = _install(monkeypatch, units, "{}")

    outcome = runner.run(dry_run=True, log=lambda *_: None)

    assert outcome.written == 0
    assert outcome.estimate["strings"] == 2
    assert outcome.estimate["est_usd"] >= 0
    assert not hasattr(fake, "groups")


def test_gender_branches_round_trip_through_the_runner(isolated, monkeypatch):
    units = _units("Greetings, $Glad:lass;!")
    reply = json.dumps(
        {"translations": [{"i": 1, "sv": "Hej, [[0]]!", "gender": [["pojke", "flicka"]]}]}
    )
    _install(monkeypatch, units, reply)

    runner.run(log=lambda *_: None)

    assert cache.read(runner.CACHE_FILE)["h0"]["sv"] == "Hej, $Gpojke:flicka;!"


def test_malformed_json_reply_is_retried_not_crashed(isolated, monkeypatch):
    units = _units("Accept")
    good = json.dumps({"translations": [{"i": 1, "sv": "Acceptera"}]})
    fake = _install(monkeypatch, units, "I'm sorry, I can't do that", retries=[good])

    outcome = runner.run(log=lambda *_: None)

    assert fake.retry_calls == 1
    assert outcome.written == 1


def test_markdown_fenced_json_is_accepted():
    parsed = batching.parse_reply('```json\n{"translations":[{"i":1,"sv":"Hej"}]}\n```')
    assert parsed[1]["sv"] == "Hej"


def test_import_file_enforces_the_same_placeholder_rules(isolated, monkeypatch, tmp_path):
    # The offline path exists so a translator with no API key (a human, or an
    # agent running on someone else's session) can fill strings in. It must not
    # be a way around the round-trip guarantee.
    monkeypatch.setattr(runner, "load_units", lambda: _units("Kill %d boars", "Give %s to %s"))
    path = tmp_path / "in.json"
    cache.write(
        path,
        {
            "items": [
                {"hash": "h0", "field": "ui", "en": "Kill %d boars", "sv": "Döda [[0]] vildsvin"},
                {"hash": "h1", "field": "ui", "en": "Give %s to %s", "sv": "Ge till"},
            ]
        },
    )

    outcome = runner.import_file(path, translator="manual", log=lambda *_: None)

    assert outcome.written == 1
    stored = cache.read(runner.CACHE_FILE)
    assert stored["h0"]["sv"] == "Döda %d vildsvin"
    assert stored["h0"]["model"] == "manual"
    assert "h1" not in stored  # dropped placeholders are rejected here too
    assert "h1" in outcome.rejected


def test_import_file_skips_blank_entries(isolated, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_units", lambda: _units("Accept"))
    path = tmp_path / "in.json"
    cache.write(path, {"items": [{"hash": "h0", "field": "ui", "en": "Accept", "sv": "  "}]})

    outcome = runner.import_file(path, translator="manual", log=lambda *_: None)

    assert outcome.written == 0
    assert outcome.rejected == {}  # blank is "not done yet", not "wrong"


def test_export_pending_round_trips_through_import(isolated, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_units", lambda: _units("Kill %d boars"))
    path = tmp_path / "pending.json"

    count = runner.export_pending(path)

    assert count == 1
    payload = cache.read(path)
    item = payload["items"][0]
    assert item["masked"] == "Kill [[0]] boars"  # the translator sees the sentinel
    assert item["sv"] == ""
    item["sv"] = "Döda [[0]] vildsvin"
    cache.write(path, payload)

    runner.import_file(path, translator="manual", log=lambda *_: None)
    assert cache.read(runner.CACHE_FILE)["h0"]["sv"] == "Döda %d vildsvin"


def test_export_pending_excludes_already_cached(isolated, monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_units", lambda: _units("Accept", "Decline"))
    cache.write(runner.CACHE_FILE, {"h0": {"sv": "Acceptera", "en": "Accept", "model": "m"}})

    count = runner.export_pending(tmp_path / "p.json")

    assert count == 1
    assert cache.read(tmp_path / "p.json")["items"][0]["en"] == "Decline"
