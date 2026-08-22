"""Placeholder masking is the toolchain's load-bearing safety property.

A dropped or reordered format specifier is a Lua error in a child's game
(spec §6), so these tests cover the failure modes explicitly rather than only
the happy path.
"""

import pytest

from common.mask import MaskError, RoundTripError, mask, restore, round_trips, validate

ROUND_TRIP_CASES = [
    "Accept",
    'Abandon "%s", destroying %s?',
    "Congratulations, you have reached level %d!",
    "You gain %1$s experience and %2$d gold.",
    "Hello $N, you brave $C.$B$BGo kill %d boars.",
    "Well met, $gsir:madam;.",
    "The $G lad:lass; from |cff00ff00Orgrimmar|r awaits.",
    "|Hquest:123:5|h[Lazy Peons]|h needs you.",
    "100%% done",
    "Kill 10 Mottled Boars then return to Gornek at the Den.",
    "|TInterface\\Icons\\Spell_Fire:16|t Fire damage",
]


@pytest.mark.parametrize("text", ROUND_TRIP_CASES)
def test_mask_restore_is_lossless(text):
    masked = mask(text)
    assert restore(masked, masked.text) == text
    assert round_trips(text)


def test_masked_text_contains_no_source_constructs():
    masked = mask("Kill %d $N boars |cffff0000now|r")
    assert "%" not in masked.text
    assert "$" not in masked.text
    assert "|" not in masked.text
    assert len(masked.tokens) == 4


def test_gender_branches_are_extracted_as_data_not_string():
    masked = mask("Greetings, $Glad:lass;!")
    assert masked.gender_branches == [("lad", "lass")]
    assert masked.has_gender


def test_gender_branches_can_be_replaced_with_translations():
    masked = mask("Greetings, $Glad:lass;!")
    out = restore(masked, "Hej, [[0]]!", [("pojke", "flicka")])
    assert out == "Hej, $Gpojke:flicka;!"


def test_gender_marker_spelling_is_preserved():
    for source in ("$Glad:lass;", "$glad:lass;", "$G lad:lass;"):
        masked = mask(f"Hi {source}")
        assert restore(masked, masked.text) == f"Hi {source}"


def test_missing_placeholder_is_rejected():
    masked = mask("Kill %d boars for %s")
    problems = validate(masked, "Döda [[0]] vildsvin")
    assert any("[[1]]" in p and "missing" in p for p in problems)
    with pytest.raises(RoundTripError):
        restore(masked, "Döda [[0]] vildsvin")


def test_reordered_bare_specifier_is_rejected():
    masked = mask("Kill %d boars for %s")
    problems = validate(masked, "För [[1]] döda [[0]]")
    assert any("reordered" in p for p in problems)


def test_reordered_positional_specifier_is_allowed():
    # `%2$d` carries its own index, so Swedish word order may legitimately move
    # it. Rejecting this would force awkward translations for no safety gain.
    masked = mask("You gain %1$s experience and %2$d gold.")
    assert validate(masked, "Du får [[1]] guld och [[0]] erfarenhet.") == []


def test_invented_placeholder_is_rejected():
    masked = mask("Kill %d boars")
    assert any("invented" in p for p in validate(masked, "Döda [[0]] och [[7]]"))


def test_duplicated_placeholder_is_rejected():
    masked = mask("Kill %d boars")
    assert any("appears 2 times" in p for p in validate(masked, "Döda [[0]] [[0]]"))


def test_source_containing_a_sentinel_is_refused():
    with pytest.raises(MaskError):
        mask("This text literally contains [[0]] already")


def test_valid_translation_passes_clean():
    masked = mask("Kill %d boars for %s")
    assert validate(masked, "Döda [[0]] vildsvin för [[1]]") == []
