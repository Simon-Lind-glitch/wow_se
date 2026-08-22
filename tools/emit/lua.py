"""Write Lua source.

The output is loaded by the game, so a quoting bug here is a dead addon. Every
string goes through `quote`; nothing is interpolated by hand.
"""

_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\0": "\\0",
}


def quote(text: str) -> str:
    """A Lua double-quoted string literal.

    Escaped explicitly rather than with repr() or json.dumps(): Lua 5.1 has no
    \\u escape, so a JSON-style encoder would emit something the game cannot
    parse the moment a control character appears.
    """
    out = []
    for char in text:
        escape = _ESCAPES.get(char)
        if escape is not None:
            out.append(escape)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\{ord(char)}")
        else:
            # Everything else, UTF-8 included, passes through. The client reads
            # these files as UTF-8 and its fonts carry å ä ö (spec §3).
            out.append(char)
    return '"' + "".join(out) + '"'


def header(*, tool_version: str, provenance: dict, purpose: str) -> str:
    """The comment block every generated file carries (spec §4)."""
    lines = [
        "-- GENERATED FILE — do not edit by hand.",
        f"-- {purpose}",
        "--",
        f"-- Written by WoWsvSE emit {tool_version}",
        f"-- Game build: {provenance['flavor']} {provenance['game_version']} "
        f"({provenance['game_build']}), Interface {provenance['interface']}",
        f"-- UI strings: {provenance['globalstrings']}",
        f"-- Quest data: {provenance['questie']} + {provenance['questtext']}",
        "--",
        "-- To change anything here, fix the toolchain and run `make all`.",
        "",
    ]
    return "\n".join(lines)
