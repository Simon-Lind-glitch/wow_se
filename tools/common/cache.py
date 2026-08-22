"""Deterministic JSON on disk.

Spec §9.3: a clean checkout must reproduce byte-identical output. Every cache
file therefore goes through one writer with sorted keys and a fixed indent, so
a rebuild that changes nothing produces no diff.
"""

import json
from pathlib import Path
from typing import Any

TOOL_VERSION = "0.1.0"


def write(path: Path | str, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def read(path: Path | str, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))
