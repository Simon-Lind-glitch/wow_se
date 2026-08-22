"""Normalization is implemented twice — Python here, Lua in the addon.

If they disagree, every lookup in the game misses and the kids see English with
no error anywhere to explain it. So both are checked against one shared vector
file rather than two copies of the cases.
"""

import pytest

from common.luadata import load
from common.normalize import is_translatable, normalize
from common.paths import REPO

VECTORS = REPO / "tests" / "fixtures" / "normalize_vectors.lua"


def _vectors():
    # Read through the same Lua bridge the extract stage uses, so the fixture
    # stays a Lua file that the busted spec can also consume directly.
    # Dense integer keys, so the bridge hands them back as nested arrays.
    return [(case[0], case[1]) for case in load(VECTORS, "--return")]


@pytest.mark.parametrize(("source", "expected"), _vectors())
def test_python_matches_the_shared_vectors(source, expected):
    assert normalize(source) == expected


def test_the_fixture_is_not_empty():
    # A silently empty fixture would make every parametrized case vanish and
    # the suite would still pass.
    assert len(_vectors()) >= 15


def test_normalize_is_idempotent():
    for source, _ in _vectors():
        once = normalize(source)
        assert normalize(once) == once


def test_untranslatable_strings_are_recognised():
    assert not is_translatable("")
    assert not is_translatable("   ")
    assert not is_translatable("%d")
    assert not is_translatable("%s / %s")
    assert not is_translatable("|cffffffff|r")
    assert is_translatable("Quest Log")
    assert is_translatable('Abandon "%s"?')
