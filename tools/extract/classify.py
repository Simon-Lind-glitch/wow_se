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

from common.normalize import is_translatable, normalize

_IDENTIFIER = re.compile(rb"\b([A-Z][A-Z0-9_]{2,})\b")

# Blizzard ships one UI source tree for every flavour, split by directory and by
# .toc suffix. A key referenced only from Mainline/Mists/Cata/Wrath code cannot
# render on a 2.5.6 client, however many times it appears.
#
# This is why the plain "is it referenced anywhere" test was too weak: it kept
# raid difficulties, pet battles and transmog, all of which are referenced —
# just never by code this client loads.
_FOREIGN_FLAVOR = re.compile(
    r"/(Mainline|Mists|Cata|Wrath)/|_(Mainline|Mists|Cata|Wrath)\.toc$", re.IGNORECASE
)
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

# Feature areas a level 1-12 pair of children cannot reach, and settings panels
# they will never open. Agreed with the requester 2026-08-22: cutting these
# removes ~1,400 strings from the corpus that nobody in this household can see.
#
# Deliberately conservative about what counts as unreachable. Talents open at
# level 10, professions and mailboxes exist in Razor Hill, and inspect is a
# right-click away — so those stay in scope even though they look like endgame
# systems from a distance.
_OUT_OF_SCOPE: tuple[tuple[str, str], ...] = (
    # Endgame and social systems.
    ("AUCTION", "auction house"),
    ("BUYOUT", "auction house"),
    ("ARENA", "arena"),
    ("BATTLEGROUND", "battlegrounds"),
    ("PVP_", "pvp"),
    ("HONOR", "pvp"),
    ("RATED", "rated pvp"),
    ("WARGAME", "pvp"),
    ("RAID_", "raids"),
    ("LFG", "group finder"),
    ("LFD", "group finder"),
    ("LFR", "group finder"),
    ("DUNGEON_", "dungeons"),
    ("CHALLENGE", "challenge modes"),
    ("SCENARIO", "scenarios"),
    ("CALENDAR", "calendar"),
    ("ACHIEVEMENT", "achievements"),
    ("CURRENCY", "currencies"),
    ("GUILDBANK", "guild bank"),
    ("GUILD_BANK", "guild bank"),
    ("BATTLEPET", "pet battles"),
    ("PET_BATTLE", "pet battles"),
    ("PETBATTLE", "pet battles"),
    ("TRANSMOG", "transmog"),
    ("ARCHAEOLOGY", "archaeology"),
    ("GLYPH", "glyphs"),
    ("GARRISON", "garrisons"),
    ("COMMUNIT", "communities"),
    ("CLUB_", "communities"),
    ("BNET", "battle.net social"),
    ("BATTLETAG", "battle.net social"),
    ("RECRUIT", "recruit a friend"),
    ("BLACKMARKET", "black market"),
    ("HEIRLOOM", "heirlooms"),
    ("STABLE", "hunter stables"),
    ("MOUNT_", "mounts, not until level 30"),
    ("VOICE", "voice chat"),
    # Settings, diagnostics and store.
    ("OPTION", "settings panel"),
    ("VIDEO", "settings panel"),
    ("GRAPHICS", "settings panel"),
    ("AUDIO", "settings panel"),
    ("SOUND_", "settings panel"),
    ("ACCESSIBILITY", "settings panel"),
    ("MACRO", "macros"),
    ("BINDING", "keybindings"),
    ("CVAR", "console variables"),
    ("ADDON", "addon manager"),
    ("SCRIPT", "diagnostics"),
    ("DEBUG", "diagnostics"),
    ("PERFORMANCE", "diagnostics"),
    ("NETWORK", "diagnostics"),
    ("HUD_", "hud editor"),
    ("UIPANEL", "internals"),
    ("BLIZZARD_", "internals"),
    ("CAA", "internals"),
    ("SPLASH", "splash screens"),
    ("BOOST", "character boost"),
    ("STORE", "in-game store"),
    ("SHOP", "in-game store"),
    ("SUBSCRIPTION", "billing"),
    ("TUTORIAL", "tutorial popups"),
    ("HELPFRAME", "help ticket"),
    ("GM_", "help ticket"),
    ("TICKET", "help ticket"),
    ("SURVEY", "help ticket"),
    ("REPORT_", "reporting players"),
)

# Strings produced outside Lua — by the server, or by the client's own C++ —
# and therefore referenced in no Lua file. The "unreferenced" rule would drop
# every one of them.
#
# Two families, both found the hard way:
#
#   * ERR_ / SPELL_FAILED_ are pushed by the server by name. These are the red
#     messages at the top of the screen ("Your bag is full", "Out of range").
#   * ITEM_ / DURABILITY / BIND_ / INVTYPE_ are assembled by the engine when it
#     builds an item tooltip. "Binds when picked up", "Durability 84 / 100",
#     "Use:", "Equip:", "+3 Stamina" — every line on every item the kids look
#     at. All of it was being skipped, which is exactly the gap the requester
#     reported as "the ui tooltips are untranslated".
#
# This exemption covers the *unreferenced* test only. A key referenced solely by
# another flavour's Lua is still out: being engine-generated does not make a
# retail feature reachable here.
_ENGINE_GENERATED: tuple[str, ...] = (
    "ERR_",
    "SPELL_FAILED_",
    "ITEM_",
    "DURABILITY",
    "BIND_",
    "INVTYPE_",
    "ENCHANT_",
)

# Keys that survive the denylist but are still not obviously safe. Flagged, not
# dropped: a human decides, per spec §5.
_REVIEW_SUFFIX: tuple[tuple[str, str], ...] = (
    ("_TEMPLATE", "format template; verify nothing parses it"),
    ("_PATTERN", "named like a parse pattern"),
    ("_FORMAT", "format string; verify nothing parses it"),
)


def _read_ui_identifiers(tarball: Path) -> tuple[set[bytes], set[bytes], set[bytes]]:
    """Identifiers in this flavour's UI source, split by whether it can load.

    Returns (referenced_by_loadable_code, used_in_find, referenced_only_elsewhere).
    Read straight out of the tarball — there is no reason to write 3,500 files
    to disk to grep them once.
    """
    native: set[bytes] = set()
    foreign: set[bytes] = set()
    parsed: set[bytes] = set()
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith((".lua", ".xml", ".toc")):
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            blob = handle.read()
            target = foreign if _FOREIGN_FLAVOR.search(member.name) else native
            target.update(_IDENTIFIER.findall(blob))
            parsed.update(_PARSE_CALL.findall(blob))
    return native, parsed, foreign - native


class Classifier:
    def __init__(
        self,
        ui_source_tarball: Path | None = None,
        *,
        already_translated: set[str] | None = None,
    ):
        # Normalized English of everything already translated. A key with a
        # translation is never dropped: narrowing the corpus must not silently
        # un-translate text that is on screen today.
        self.already_translated = already_translated or set()
        self.referenced: set[bytes] = set()
        self.parsed: set[bytes] = set()
        self.other_flavor: set[bytes] = set()
        if ui_source_tarball is not None and ui_source_tarball.exists():
            self.referenced, self.parsed, self.other_flavor = _read_ui_identifiers(
                ui_source_tarball
            )

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

        # Exempt from the SCOPE filters only, and only below the denylist above.
        #
        # Placing this before the denylist let a translated word re-admit a
        # forbidden key: "Yell" -> "Ropa" pulled CHAT_MSG_YELL back into the
        # corpus, and `make guard` failed the build on it. The safety rules are
        # not negotiable by coincidence of shared wording.
        exempt = normalize(value) in self.already_translated

        encoded = key.encode()
        engine_generated = key.startswith(_ENGINE_GENERATED)
        if self.has_ui_source:
            if encoded in self.other_flavor and not exempt:
                return Decision(
                    Verdict.SKIP,
                    "referenced only by code for another flavour; cannot render here",
                )
            if encoded not in self.referenced and not engine_generated and not exempt:
                return Decision(
                    Verdict.SKIP,
                    "not referenced anywhere in this flavour's UI source; cannot render",
                )
            if encoded in self.parsed:
                return Decision(
                    Verdict.REVIEW,
                    "used inside a find/match/gsub call; likely a parse pattern (spec §5)",
                )

        for prefix, area in _OUT_OF_SCOPE:
            if key.startswith(prefix) and not exempt:
                return Decision(Verdict.SKIP, f"out of scope: {area}")

        # The _TEMPLATE/_FORMAT suffix check is a guess from the name. For an
        # engine-generated string we have positive evidence it is display text —
        # the engine draws it — so the guess does not get to override that.
        # DURABILITY_TEMPLATE is the case in point: it is the durability line on
        # every item tooltip, and flagging it for review meant never shipping it.
        # The find/match evidence above still applies; that is measured, not
        # guessed.
        if not engine_generated:
            for suffix, reason in _REVIEW_SUFFIX:
                if key.endswith(suffix):
                    return Decision(Verdict.REVIEW, reason)

        return Decision(Verdict.TRANSLATE, "user-visible chrome")
