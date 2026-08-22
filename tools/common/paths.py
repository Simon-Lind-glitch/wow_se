"""Canonical repository paths.

Everything is derived from this file's own location so the toolchain works from
any working directory, which `make` relies on.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "tools"
CACHE = TOOLS / "cache"

# Raw upstream artifacts. Gitignored: large, and re-fetchable from the pins in
# extract/sources.py.
DOWNLOADS = CACHE / "downloads"

# Extracted source strings and finished translations. Both committed, so a clean
# checkout reproduces byte-identical output with no API calls (spec §9.3).
SOURCE = CACHE / "source"
TRANSLATIONS = CACHE / "translations"

ADDON = REPO / "addon" / "WoWsvSE"
GLOSSARY = TOOLS / "glossary.sv.yaml"
LUA_HELPERS = TOOLS / "common" / "lua"


def ensure_dirs() -> None:
    for d in (DOWNLOADS, SOURCE, TRANSLATIONS):
        d.mkdir(parents=True, exist_ok=True)
