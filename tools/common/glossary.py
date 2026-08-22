"""The locked term glossary (`tools/glossary.sv.yaml`).

Loaded once and rendered into the system prompt, so every request in a batch
sees the same vocabulary. Also used after translation to report where a cached
Swedish string disagrees with a term that has since been locked or changed.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from common.paths import GLOSSARY


@dataclass(frozen=True)
class Glossary:
    version: int
    terms: dict[str, str]
    keep_english: tuple[str, ...]

    def prompt_block(self) -> str:
        """The glossary as prompt text, deterministically ordered.

        Order matters for prompt caching: a dict iterated in insertion order
        would reshuffle whenever the YAML is reordered, silently invalidating
        the cached prefix on every request.
        """
        terms = "\n".join(f"  {en} -> {sv}" for en, sv in sorted(self.terms.items()))
        keep = "\n".join(f"  {name}" for name in sorted(self.keep_english))
        return f"LOCKED TERMS (use exactly these):\n{terms}\n\nNEVER TRANSLATE:\n{keep}"

    def violations(self, english: str, swedish: str) -> list[str]:
        """Locked terms present in the source but rendered differently in output.

        Deliberately advisory, not a hard failure: Swedish inflects, so
        "uppdrag" legitimately appears as "uppdraget" or "uppdragen", and
        demanding an exact substring would reject correct Swedish. Findings go
        in a report a human reads.
        """
        problems = []
        lower_en, lower_sv = english.lower(), swedish.lower()
        for term, expected in self.terms.items():
            if not re.search(rf"\b{re.escape(term.lower())}\b", lower_en):
                continue
            # Match the stem so ordinary Swedish inflection passes.
            stem = expected.lower()[: max(4, len(expected) - 2)]
            if stem and stem not in lower_sv:
                problems.append(f"{term!r} should render as {expected!r}")
        for name in self.keep_english:
            if name.lower() in lower_en and name.lower() not in lower_sv:
                problems.append(f"proper noun {name!r} was dropped or translated")
        return problems


@lru_cache(maxsize=1)
def load() -> Glossary:
    data = yaml.safe_load(GLOSSARY.read_text(encoding="utf-8"))
    return Glossary(
        version=int(data["version"]),
        terms=dict(data["terms"]),
        keep_english=tuple(data["keep_english"]),
    )
