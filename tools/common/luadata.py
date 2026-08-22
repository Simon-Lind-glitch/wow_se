"""Load upstream Lua source as Python data.

Delegates to `common/lua/dump.lua` running under real Lua 5.1 — the same
interpreter version the game uses — rather than parsing Lua with regexes. See
that file's header for why.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from common.paths import LUA_HELPERS

LUA = "lua5.1"
_DUMPER = LUA_HELPERS / "dump.lua"
_QUESTIE_DUMPER = LUA_HELPERS / "dump_questie.lua"


class LuaLoadError(RuntimeError):
    pass


def load(path: Path, global_name: str | None = None) -> Any:
    """Execute `path` in a sandboxed Lua environment and return its data.

    With `global_name`, returns that global (one level of `a.b` dotted lookup is
    supported). Without, returns every string-valued global the file assigned.
    """
    cmd = [LUA, str(_DUMPER), str(path)]
    if global_name:
        cmd.append(global_name)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise LuaLoadError(f"{path.name}: {proc.stderr.strip() or f'exit {proc.returncode}'}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - a dumper bug, not input
        raise LuaLoadError(f"{path.name}: dumper emitted invalid JSON: {exc}") from exc


def load_questie(path: Path, which: str) -> Any:
    """Load one table out of a Questie database file.

    Questie needs its own entry point: it expects the addon environment, and it
    stores the quest table as a Lua chunk inside a string. `which` is a
    `QuestieDB` field name, e.g. `questData` or `questKeys`.
    """
    proc = subprocess.run(
        [LUA, str(_QUESTIE_DUMPER), str(path), which],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise LuaLoadError(f"{path.name} [{which}]: {proc.stderr.strip() or proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - a dumper bug, not input
        raise LuaLoadError(f"{path.name} [{which}]: dumper emitted invalid JSON: {exc}") from exc
