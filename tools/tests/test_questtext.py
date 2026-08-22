"""The world-DB parser handles adversarial input: quest prose is full of
apostrophes, escaped quotes, parentheses and embedded newlines.
"""

import gzip

import pytest

from extract.questtext import DumpError, _split_tuples, load

HEADER = """CREATE TABLE `quest_template` (
  `entry` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `ZoneOrSort` smallint(6) NOT NULL DEFAULT '0',
  `QuestLevel` smallint(6) NOT NULL DEFAULT '0',
  `Title` text,
  `Details` text,
  `Objectives` text,
  `RequestItemsText` text,
  `OfferRewardText` text,
  `EndText` text
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
"""


def _dump(tmp_path, rows: str):
    path = tmp_path / "world.sql.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(HEADER)
        handle.write(f"INSERT INTO `quest_template` VALUES {rows};\n")
    return path


def test_unquoted_null_is_absent_not_the_word():
    # Regression: an unquoted NULL used to become the literal string "NULL",
    # which would have been translated and shown in a child's quest log.
    rows = _split_tuples("(1,14,2,'Title','Details','Objectives',NULL,'Reward',NULL)")
    assert rows[0][6] is None
    assert rows[0][8] is None


def test_quoted_null_is_the_word():
    rows = _split_tuples("(1,14,2,'NULL','x','y','z','w','v')")
    assert rows[0][3] == "NULL"


def test_apostrophes_and_escaped_quotes_survive():
    rows = _split_tuples(r"(1,14,2,'Hana\'zua','He said \"go\"','a,b (c)','p','q','r')")
    assert rows[0][3] == "Hana'zua"
    assert rows[0][4] == 'He said "go"'
    # A comma and parentheses inside a quoted value must not split the row.
    assert rows[0][5] == "a,b (c)"


def test_escaped_newline_becomes_a_real_newline():
    rows = _split_tuples(r"(1,14,2,'t','line1\nline2','o','p','q','r')")
    assert rows[0][4] == "line1\nline2"


def test_multiple_rows_in_one_insert():
    rows = _split_tuples("(1,14,2,'a','b','c','d','e','f'),(2,363,3,'g','h','i','j','k','l')")
    assert len(rows) == 2
    assert rows[1][0] == "2"


def test_load_filters_to_wanted_ids(tmp_path):
    path = _dump(
        tmp_path,
        "(788,363,2,'Cutting Teeth','Details here','Kill boars',NULL,'Well done',NULL),"
        "(999,14,5,'Other','x','y',NULL,'z',NULL)",
    )
    out = load(path, wanted_ids={788})
    assert set(out) == {788}
    quest = out[788]
    assert quest.title == "Cutting Teeth"
    assert quest.description == "Details here"
    assert quest.objectives == "Kill boars"
    assert quest.progress == ""  # NULL -> absent -> empty, never "NULL"
    assert quest.completion == "Well done"


def test_missing_column_is_a_hard_error(tmp_path):
    path = tmp_path / "bad.sql.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("CREATE TABLE `quest_template` (\n  `entry` int\n) ENGINE=MyISAM;\n")
        handle.write("INSERT INTO `quest_template` VALUES (1);\n")
    with pytest.raises(DumpError, match="missing columns"):
        load(path)
