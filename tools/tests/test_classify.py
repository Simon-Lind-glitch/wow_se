"""§5 triage. The dangerous mistakes are translating a slash command (breaks
every macro) and dropping a server-pushed error string (invisible to a grep of
the client's Lua, but the most useful text on screen).
"""

from extract.classify import Classifier, Verdict


def verdict(key, value, classifier=None):
    return (classifier or Classifier()).classify(key, value).verdict


def test_slash_commands_are_never_translated():
    assert verdict("SLASH_CAST1", "/cast") is Verdict.SKIP


def test_voice_macros_are_skipped_they_go_to_other_players():
    assert verdict("VOICEMACRO_HELLO_ORC_MALE_1", "Throm'ka!") is Verdict.SKIP


def test_combat_log_templates_are_skipped():
    assert verdict("COMBATLOG_DISHONORGAIN", "%s dies, dishonorable kill.") is Verdict.SKIP


def test_loot_patterns_are_skipped_other_addons_parse_them():
    assert verdict("LOOT_ITEM_SELF", "You receive loot: %s.") is Verdict.SKIP


def test_plain_chrome_is_translated():
    assert verdict("QUEST_LOG", "Quest Log") is Verdict.TRANSLATE


def test_value_equal_to_key_is_skipped():
    assert verdict("DND", "DND") is Verdict.SKIP


def test_content_free_values_are_skipped():
    assert verdict("SOME_KEY", "%d") is Verdict.SKIP
    assert verdict("TIME_UNIT_DELIMITER", " ") is Verdict.SKIP


def test_format_templates_are_flagged_for_review_not_dropped():
    assert verdict("UNIT_TYPE_LEVEL_TEMPLATE", "Level %d %s") is Verdict.REVIEW


def test_server_pushed_errors_survive_the_unreferenced_rule():
    # ERR_* never appears in client Lua — the server sends it by name. Without
    # the exemption these are all dropped, which is the bug this guards.
    classifier = Classifier()
    classifier.referenced = {b"QUEST_LOG"}  # pretend a UI index that omits ERR_*
    assert classifier.classify("ERR_INV_FULL", "Inventory is full.").verdict is Verdict.TRANSLATE
    assert classifier.classify("GARRISON_MISSIONS", "Missions").verdict is Verdict.SKIP


def test_keys_used_in_find_calls_are_flagged():
    classifier = Classifier()
    classifier.referenced = {b"SOME_PATTERN_KEY"}
    classifier.parsed = {b"SOME_PATTERN_KEY"}
    decision = classifier.classify("SOME_PATTERN_KEY", "You have slain %s.")
    assert decision.verdict is Verdict.REVIEW
    assert "parse pattern" in decision.reason


def test_an_existing_translation_never_re_admits_a_forbidden_key():
    """Regression: `make guard` failed the v0.4.0 build on this.

    The scope filter exempts keys that already have a translation, so
    narrowing the corpus cannot un-translate text that is on screen. Placed
    before the safety denylist, that exemption let a translated word drag a
    forbidden key back in: "Yell" -> "Ropa" re-admitted CHAT_MSG_YELL, and
    emitting a CHAT_MSG_* assignment is exactly what spec §2 forbids.
    """
    classifier = Classifier(already_translated={"Yell"})
    assert classifier.classify("CHAT_MSG_YELL", "Yell").verdict is Verdict.SKIP
    assert classifier.classify("SLASH_YELL1", "Yell").verdict is Verdict.SKIP
    assert classifier.classify("COMBATLOG_YELL", "Yell").verdict is Verdict.SKIP


def test_an_existing_translation_does_survive_the_scope_filter():
    # The exemption must still do its job for ordinary keys.
    classifier = Classifier(already_translated={"Options"})
    assert classifier.classify("OPTION_TOOLTIP_X", "Options").verdict is Verdict.TRANSLATE
    # ...and a key with no translation is still cut by scope.
    assert classifier.classify("OPTION_TOOLTIP_Y", "Something else").verdict is Verdict.SKIP
