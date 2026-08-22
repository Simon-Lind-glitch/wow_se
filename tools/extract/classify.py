"""Decide which GlobalStrings keys may be translated.

Spec §5: "Translate only keys that render as user-visible text. Skip keys used
as pattern templates for parsing (anything matched with `string.find` by
convention — flag ambiguous cases for human review rather than guessing)."

There are 18,260 keys in the 2.5.6 dump. Three things make blanket translation
wrong rather than merely expensive:

* `SLASH_*` values *are* the slash commands. `SLASH_CAST1 = "/cast"`. Translate
  those and every macro the kids write, and every macro on every guide, stops
  working.
* `VOICEMACRO_*` and emote strings are text sent to *other players*. Swedish
  there is not a reading aid, it is noise in a stranger's chat window.
* `COMBATLOG_*` and `ACTION_*` are combat-log format templates. Spec §3
  forbids touching strings other addons parse.

Everything else is decided from evidence rather than a prefix hunch: a key that
appears nowhere in this flavour's own UI source cannot be rendered by this
client, and a key used inside a `string.find` call is a parse pattern.
"""

import re
import tarfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from common.normalize import is_translatable

_IDENTIFIER = re.compile(rb"\b([A-Z][A-Z0-9_]{2,})\b")
# `string.find(msg, ERR_SOMETHING)` / `msg:match(PATTERN_KEY)` and friends.
_PARSE_CALL = re.compile(rb"(?:find|match|gmatch|gsub)\s*\([^()]{0,200}?\b([A-Z][A-Z0-9_]{2,})\b")


class Verdict(str, Enum):
    TRANSLATE = "translate"
    REVIEW = "review"
    SKIP = "skip"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str


# Prefixes that are never translated, with the reason recorded so the decision
# is auditable rather than folklore.
_DENY_PREFIX: tuple[tuple[str, str], ...] = (
    ("SLASH_", "value is the slash command itself; translating breaks macros"),
    ("VOICEMACRO_", "sent to other players' chat, not shown to us"),
    ("EMOTE", "sent to other players' chat, not shown to us"),
    ("COMBATLOG_", "combat log format template (spec §3)"),
    ("ACTION_", "combat log format template (spec §3)"),
    ("CHAT_MSG_", "chat event plumbing; never render (spec §2)"),
    ("LOOT_ITEM", "parsed from chat by loot addons (spec §3)"),
    ("BINDING_HEADER_", "key-binding internals"),
    ("KEY_", "physical key names; must match the keyboard"),
    ("LOCALE_", "locale plumbing"),
    ("FONT_", "font configuration, not prose"),
)

# Strings the *server* pushes by name — they appear in no client-side Lua, so
# the "unreferenced" rule would wrongly drop all 1,100+ of them. These are the
# red messages at the top of the screen ("Your bag is full", "You are too far
# away"), which is precisely the text a nine-year-old needs in Swedish.
_SERVER_PUSHED: tuple[str, ...] = (
    "ERR_",
    "SPELL_FAILED_",
)

# Keys that survive the denylist but are still not obviously safe. Flagged, not
# dropped: a human decides, per spec §5.
_REVIEW_SUFFIX: tuple[tuple[str, str], ...] = (
    ("_TEMPLATE", "format template; verify nothing parses it"),
    ("_PATTERN", "named like a parse pattern"),
    ("_FORMAT", "format string; verify nothing parses it"),
)


def _read_ui_identifiers(tarball: Path) -> tuple[set[bytes], set[bytes]]:
    """Identifiers referenced by this flavour's UI source, and parse-pattern uses.

    Returns (referenced, used_in_find). Read straight out of the tarball — there
    is no reason to write 3,500 files to disk to grep them once.
    """
    referenced: set[bytes] = set()
    parsed: set[bytes] = set()
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith((".lua", ".xml", ".toc")):
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            blob = handle.read()
            referenced.update(_IDENTIFIER.findall(blob))
            parsed.update(_PARSE_CALL.findall(blob))
    return referenced, parsed


class Classifier:
    def __init__(self, ui_source_tarball: Path | None = None):
        self.referenced: set[bytes] = set()
        self.parsed: set[bytes] = set()
        if ui_source_tarball is not None and ui_source_tarball.exists():
            self.referenced, self.parsed = _read_ui_identifiers(ui_source_tarball)

    @property
    def has_ui_source(self) -> bool:
        return bool(self.referenced)

    def classify(self, key: str, value: str) -> Decision:
        if value == key:
            return Decision(Verdict.SKIP, "value is the key; a placeholder or test string")
        if not is_translatable(value):
            return Decision(Verdict.SKIP, "no natural-language content")
        for prefix, reason in _DENY_PREFIX:
            if key.startswith(prefix):
                return Decision(Verdict.SKIP, reason)

        encoded = key.encode()
        server_pushed = key.startswith(_SERVER_PUSHED)
        if self.has_ui_source:
            if encoded not in self.referenced and not server_pushed:
                return Decision(
                    Verdict.SKIP,
                    "not referenced anywhere in this flavour's UI source; cannot render",
                )
            if encoded in self.parsed:
                return Decision(
                    Verdict.REVIEW,
                    "used inside a find/match/gsub call; likely a parse pattern (spec §5)",
                )

        for suffix, reason in _REVIEW_SUFFIX:
            if key.endswith(suffix):
                return Decision(Verdict.REVIEW, reason)

        return Decision(Verdict.TRANSLATE, "user-visible chrome")
