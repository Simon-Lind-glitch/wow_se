"""Normalize a client string into its lookup key.

This algorithm is implemented **twice**: here, and in `addon/WoWsvSE/core.lua`
as `SVSE.Normalize`. They must agree exactly or every lookup misses. The
agreement is not assumed — `tools/tests/test_normalize.py` and
`tests/normalize_spec.lua` both run the same vector file
(`tests/fixtures/normalize_vectors.lua`), so a drift in either implementation
fails `make test`.

Only ASCII whitespace classes are used, because Lua 5.1's `%s` is ASCII-only and
Python's `\\s` is not.
"""

import re

# |cAARRGGBB ... |r  — colour wrapping. Stripped for keying, reapplied on render.
_COLOR_OPEN = re.compile(r"\|c[0-9a-fA-F]{8}")
_COLOR_CLOSE = re.compile(r"\|r")

# |Hquest:123:60|h[Kill Boars]|h — keep the display text, drop the link payload.
_HYPERLINK = re.compile(r"\|H.*?\|h(.*?)\|h")

# |TInterface\Icons\foo:16|t — inline texture, no textual content.
_TEXTURE = re.compile(r"\|T.*?\|t")

_WHITESPACE = re.compile(r"[ \t\r\n\f\v]+")


def normalize(text: str) -> str:
    """Strip presentation, collapse whitespace, trim.

    Without this, the same sentence rendered in two colours would occupy two
    cache entries and cost two translations (spec §7).
    """
    if not text:
        return ""
    text = _HYPERLINK.sub(r"\1", text)
    text = _TEXTURE.sub("", text)
    text = _COLOR_OPEN.sub("", text)
    text = _COLOR_CLOSE.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def is_translatable(text: str) -> bool:
    """False for strings with no natural-language content to translate.

    Pure punctuation, pure format specifiers and bare numbers are rendered
    as-is; sending them to a model wastes tokens and invites damage.
    """
    stripped = normalize(text)
    if not stripped:
        return False
    # Needs at least one run of two letters to be a word rather than a symbol.
    return re.search(r"[A-Za-z]{2}", stripped) is not None
