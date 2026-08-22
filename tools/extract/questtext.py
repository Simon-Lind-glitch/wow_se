"""Quest prose from the cmangos TBC world database.

Questie carries quest *titles* and *objectives text* but no description,
progress or completion prose — see the §6 correction in SPEC.md. Those three
come from `quest_template` in the cmangos TBC dump, keyed by the same numeric
quest ID Questie uses.

The dump is a ~200 MB MySQL script inside an 18 MB gzip, so it is streamed and
only `quest_template` is parsed. Nothing is written to disk uncompressed.
"""

import gzip
import re
from dataclasses import dataclass
from pathlib import Path

_CREATE = "CREATE TABLE `quest_template`"
_INSERT = "INSERT INTO `quest_template`"

# Columns we need. Resolved by name from the CREATE TABLE, never by hardcoded
# index — the dump gains columns between releases.
_FIELDS = {
    "entry": "id",
    "ZoneOrSort": "zone_or_sort",
    "QuestLevel": "quest_level",
    "Title": "title",
    "Details": "description",
    "Objectives": "objectives",
    "RequestItemsText": "progress",
    "OfferRewardText": "completion",
    "EndText": "end_text",
}


@dataclass
class QuestText:
    id: int
    zone_or_sort: int
    quest_level: int
    title: str
    description: str
    objectives: str
    progress: str
    completion: str
    end_text: str


class DumpError(RuntimeError):
    pass


def _parse_columns(header: str) -> list[str]:
    return re.findall(r"^\s*`(\w+)`\s", header, re.M)


def _split_tuples(values: str) -> list[list[str | None]]:
    """Split a MySQL `VALUES (...),(...)` body into per-row value lists.

    Hand-rolled rather than regex: quest prose is full of apostrophes,
    parentheses and escaped quotes, and every regex shortcut here corrupts a
    handful of rows out of thousands without saying so.
    """
    rows: list[list[str | None]] = []
    current: list[str | None] = []
    field: list[str] = []
    in_string = False
    escaped = False
    quoted = False
    depth = 0

    def flush() -> None:
        """Close the current field.

        An *unquoted* NULL is a real absent value; a quoted 'NULL' would be the
        four-letter word. Conflating them means shipping the string "NULL" to
        the translator and then into a child's quest log, which is exactly what
        happened before this distinction existed.
        """
        text = "".join(field)
        current.append(None if not quoted and text == "NULL" else text)

    for ch in values:
        if in_string:
            if escaped:
                # MySQL escapes: \n \r \t \\ \' \" \0 \Z
                field.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0", "Z": "\x1a"}.get(ch, ch))
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_string = False
            else:
                field.append(ch)
            continue

        if ch == "'":
            in_string = True
            quoted = True
        elif ch == "(":
            depth += 1
            if depth == 1:
                current, field, quoted = [], [], False
        elif ch == ")":
            depth -= 1
            if depth == 0:
                flush()
                rows.append(current)
                current, field, quoted = [], [], False
        elif ch == "," and depth == 1:
            flush()
            field, quoted = [], False
        elif depth == 1 and not ch.isspace():
            field.append(ch)

    return rows


def load(dump: Path, *, wanted_ids: set[int] | None = None) -> dict[int, QuestText]:
    """Stream the dump and return quest text, optionally only for `wanted_ids`."""
    columns: list[str] | None = None
    header: list[str] = []
    reading_header = False
    out: dict[int, QuestText] = {}

    with gzip.open(dump, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if columns is None:
                if line.startswith(_CREATE):
                    reading_header = True
                if reading_header:
                    header.append(line)
                    if line.startswith(")"):
                        columns = _parse_columns("".join(header))
                        missing = set(_FIELDS) - set(columns)
                        if missing:
                            raise DumpError(f"quest_template is missing columns: {sorted(missing)}")
                        reading_header = False
                continue

            if not line.startswith(_INSERT):
                continue

            body = line[line.index("VALUES") + len("VALUES") :]
            index = {name: columns.index(name) for name in _FIELDS}
            for row in _split_tuples(body):
                if len(row) != len(columns):
                    continue  # a truncated tail line; the next INSERT carries it
                try:
                    quest_id = int(row[index["entry"]] or 0)
                except ValueError:
                    continue
                if wanted_ids is not None and quest_id not in wanted_ids:
                    continue
                out[quest_id] = QuestText(
                    id=quest_id,
                    zone_or_sort=int(row[index["ZoneOrSort"]] or 0),
                    quest_level=int(row[index["QuestLevel"]] or 0),
                    title=row[index["Title"]] or "",
                    description=row[index["Details"]] or "",
                    objectives=row[index["Objectives"]] or "",
                    progress=row[index["RequestItemsText"]] or "",
                    completion=row[index["OfferRewardText"]] or "",
                    end_text=row[index["EndText"]] or "",
                )

    if not out:
        raise DumpError(f"no quest_template rows parsed from {dump.name}")
    return out
