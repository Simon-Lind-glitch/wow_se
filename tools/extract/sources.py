"""Pinned upstream sources. The single place these are defined (SPEC.md §0).

Every source is pinned to a commit SHA, not a branch. A branch would mean a
rebuild silently picks up a different game build, and the emitted addon would no
longer match the `## Interface` number it claims.

Bumping a pin is a deliberate act, done once per game patch: change the SHA
here, re-run `make all`, and read the diff.
"""

import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from common.paths import DOWNLOADS

# --- The game build this addon is generated for (SPEC.md §0) ------------------
# From the client itself: GetBuildInfo() => "2.5.6", "69110", 20506
FLAVOR = "TBC Anniversary"
PRODUCT = "wow_anniversary"
GAME_VERSION = "2.5.6"
GAME_BUILD = "69110"
INTERFACE = 20506

# --- Upstream artifacts ------------------------------------------------------


@dataclass(frozen=True)
class Source:
    name: str
    repo: str
    sha: str
    path: str
    note: str

    @property
    def url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repo}/{self.sha}/{self.path}"

    @property
    def local(self) -> Path:
        return DOWNLOADS / f"{self.name}{Path(self.path).suffix}"


# The client's enUS GlobalStrings. Not in Blizzard's own UI-source dump — that
# dump ships the frame-layout `Localization.lua` files but not the string table
# itself, which lives in CASC. Ketho's repo extracts it per flavor.
GLOBALSTRINGS = Source(
    name="globalstrings_enUS",
    repo="Ketho/BlizzardInterfaceResources",
    sha="d6d4a8f445f198c5c73ff5f8f5002ad8f04451e4",
    path="Resources/GlobalStrings/enUS.lua",
    note="client GlobalStrings, enUS, 2.5.6",
)

# Questie's TBC quest database: quest titles, objectives text, and — crucially —
# `zoneOrSort`, which is what tells us a quest belongs to Durotar.
QUESTIE_QUESTS = Source(
    name="questie_tbc_questdb",
    repo="Questie/Questie",
    sha="4aea09ec3fe59b2ef46b83befc7bffe7bb478cc6",
    path="Database/TBC/tbcQuestDB.lua",
    note="Questie TBC quest DB",
)

# Questie's field-order table. The quest DB is positional arrays; this maps
# position -> field name. Reading it beats hardcoding indices that shift.
QUESTIE_KEYS = Source(
    name="questie_questkeys",
    repo="Questie/Questie",
    sha="4aea09ec3fe59b2ef46b83befc7bffe7bb478cc6",
    path="Database/questDB.lua",
    note="Questie questKeys field order",
)

# Blizzard's UI source for this exact flavor. Used only to decide which
# GlobalStrings keys this client actually renders: the dump contains thousands of
# retail-only keys (GARRISON_, COMMUNITIES_, BOOST2_) that no 2.5.6 panel ever
# shows. Translating those would be money spent on invisible text.
UI_SOURCE_TARBALL = Source(
    name="ui_source",
    repo="Gethe/wow-ui-source",
    sha="e9bbe81652a6",
    path="",  # tarball, see url override below
    note="Blizzard UI source, classic_anniversary 2.5.6",
)

UI_SOURCE_URL = "https://codeload.github.com/Gethe/wow-ui-source/tar.gz/e9bbe81652a6"

# The cmangos TBC world database. Supplies the three quest prose fields Questie
# does not carry: Details (description), RequestItemsText (progress) and
# OfferRewardText (completion). See the §6 correction in SPEC.md.
CMANGOS_DB = Source(
    name="tbcdb",
    repo="cmangos/tbc-db",
    sha="da2de07e6606d495872c3fd92ba8363cf79f43c9",
    path="Full_DB/TBCDB_1.11.0_Vengeance_One_A_Cmangos_Story.sql.gz",
    note="cmangos TBC world DB, quest_template",
)


class FetchError(RuntimeError):
    pass


def fetch(source: Source, *, url: str | None = None, force: bool = False) -> Path:
    """Download a pinned source into the (gitignored) download cache.

    Idempotent: an existing file is reused, because these are content-pinned by
    SHA and cannot change under us.
    """
    dest = source.local
    if url:
        dest = DOWNLOADS / f"{source.name}.tar.gz"
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = url or source.url
    try:
        with urllib.request.urlopen(target, timeout=120) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise FetchError(
            f"could not fetch {source.name} from {target}: {exc}\n"
            "This stage needs network access. `make emit` and `make verify` do not."
        ) from exc
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(dest)
    return dest


def provenance() -> dict[str, str]:
    """Header material for generated files, so any output names its inputs."""
    return {
        "flavor": FLAVOR,
        "product": PRODUCT,
        "game_version": GAME_VERSION,
        "game_build": GAME_BUILD,
        "interface": str(INTERFACE),
        "globalstrings": f"{GLOBALSTRINGS.repo}@{GLOBALSTRINGS.sha[:8]}",
        "questie": f"{QUESTIE_QUESTS.repo}@{QUESTIE_QUESTS.sha[:8]}",
        "questtext": f"{CMANGOS_DB.repo}@{CMANGOS_DB.sha[:8]}",
    }
