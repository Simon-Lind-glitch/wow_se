"""Placeholder masking and round-trip verification.

The single most dangerous thing this toolchain does is hand game text to a
language model. Format specifiers (`%s`, `%1$d`) are consumed by
`string.format` at runtime, so a dropped or reordered one is a Lua error in the
child's face, not a typo. Quest tokens (`$N`, `$B`, `$G a:b;`) are expanded by
the client.

So: every such construct is replaced by an opaque sentinel before translation
and restored after, and any output whose sentinel set does not round-trip
exactly is rejected (spec §6). Rejection is a hard failure by design — the
translate stage retries, and gives up rather than shipping a broken string.

`$G` is deliberately *not* passed through as a string. Its two branches are
extracted as structured data, translated as their own units, and recombined,
because Swedish adjective agreement does not line up with English (spec §6).
"""

import re
from dataclasses import dataclass, field

# Sentinels are bracketed digits: short, ASCII, and something models reliably
# copy verbatim. Anything a model *might* translate (words, quotes) is unusable.
_SENTINEL = "[[{}]]"
_SENTINEL_RE = re.compile(r"\[\[(\d+)\]\]")

# One combined scanner, alternation ordered most-specific first.
_SCANNER = re.compile(
    r"""
    (?P<gender>\$[Gg]\s*[^:;]*:[^;]*;)
  | (?P<escape>
        \|c[0-9a-fA-F]{8}      # |cffRRGGBB colour open
      | \|r                    # colour close
      | \|H.*?\|h              # hyperlink payload
      | \|T.*?\|t              # inline texture
      | \|n                    # explicit newline escape
    )
  | (?P<fmt>
        %%                     # literal percent
      | %(?P<pos>\d+\$)?[-+ #0']*\d*(?:\.\d+)?[diouxXeEfgGcsq]
    )
  | (?P<quest>\$[BbNnCcRrPp])
    """,
    re.VERBOSE,
)

_GENDER_BRANCHES = re.compile(r"\$[Gg]\s*(?P<male>[^:;]*):(?P<female>[^;]*);")


class MaskError(Exception):
    """The source string cannot be masked safely."""


class RoundTripError(Exception):
    """Translated output did not preserve the masked constructs."""


@dataclass(frozen=True)
class Token:
    raw: str
    kind: str  # gender | escape | fmt | fmt_positional | quest


@dataclass
class Masked:
    """A source string with every machine-read construct replaced by a sentinel."""

    text: str
    tokens: list[Token] = field(default_factory=list)
    # English (male, female) branch pairs, positionally matched to the gender
    # tokens in `tokens`, in order of appearance.
    gender_branches: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_gender(self) -> bool:
        return bool(self.gender_branches)


def mask(text: str) -> Masked:
    """Replace format specifiers, quest tokens and escapes with sentinels."""
    if _SENTINEL_RE.search(text):
        raise MaskError(f"source already contains a sentinel-shaped substring: {text!r}")

    out: list[str] = []
    tokens: list[Token] = []
    genders: list[tuple[str, str]] = []
    pos = 0

    for m in _SCANNER.finditer(text):
        out.append(text[pos : m.start()])
        raw = m.group(0)
        if m.lastgroup and m.group("gender"):
            kind = "gender"
            branches = _GENDER_BRANCHES.match(raw)
            if not branches:  # pragma: no cover - the scanner guarantees a match
                raise MaskError(f"unparseable gender token: {raw!r}")
            genders.append((branches.group("male"), branches.group("female")))
        elif m.group("escape"):
            kind = "escape"
        elif m.group("fmt"):
            # Bare `%s` is order-sensitive; `%1$s` carries its own index and may
            # legitimately move when Swedish word order differs.
            kind = "fmt_positional" if m.group("pos") else "fmt"
        else:
            kind = "quest"
        out.append(_SENTINEL.format(len(tokens)))
        tokens.append(Token(raw=raw, kind=kind))
        pos = m.end()

    out.append(text[pos:])
    return Masked(text="".join(out), tokens=tokens, gender_branches=genders)


def validate(masked: Masked, translated: str) -> list[str]:
    """Return human-readable problems with a translation, empty if it is sound.

    Returned strings are fed back to the model on retry, so they name the
    offending sentinel rather than just saying "invalid".
    """
    problems: list[str] = []
    found = [int(i) for i in _SENTINEL_RE.findall(translated)]
    expected = set(range(len(masked.tokens)))

    for idx in sorted(expected - set(found)):
        problems.append(f"placeholder [[{idx}]] ({masked.tokens[idx].raw!r}) is missing")
    for idx in sorted(set(found) - expected):
        problems.append(f"placeholder [[{idx}]] was invented and has no source construct")
    for idx in sorted(expected & set(found)):
        n = found.count(idx)
        if n > 1:
            problems.append(f"placeholder [[{idx}]] appears {n} times, expected once")

    ordered = [i for i in found if i in expected and masked.tokens[i].kind == "fmt"]
    original_order = [i for i, t in enumerate(masked.tokens) if t.kind == "fmt"]
    if ordered != [i for i in original_order if i in ordered]:
        problems.append(
            "non-positional format specifiers were reordered; "
            f"expected {original_order} in order, got {ordered}"
        )
    return problems


def restore(
    masked: Masked,
    translated: str,
    gender_branches: list[tuple[str, str]] | None = None,
) -> str:
    """Put the original constructs back. Raises unless the round trip is exact.

    `gender_branches` supplies translated (male, female) pairs, positionally
    matched to the source's gender tokens. Omit it and the English branches are
    kept, which is wrong-but-safe rather than broken.
    """
    problems = validate(masked, translated)
    if problems:
        raise RoundTripError("; ".join(problems))

    gender_seen = 0
    gender_out = gender_branches or []

    def replace(m: re.Match[str]) -> str:
        nonlocal gender_seen
        token = masked.tokens[int(m.group(1))]
        if token.kind != "gender":
            return token.raw
        branches = _GENDER_BRANCHES.match(token.raw)
        if not branches:  # pragma: no cover - mask() already parsed this
            raise RoundTripError(f"unparseable gender token: {token.raw!r}")
        # Keep the source's exact spelling of the marker, whitespace included:
        # "$G " and "$g" both occur, and the client is picky.
        prefix = token.raw[: branches.start("male")]
        if gender_seen < len(gender_out):
            male, female = gender_out[gender_seen]
        else:
            male, female = masked.gender_branches[gender_seen]
        gender_seen += 1
        return f"{prefix}{male}:{female};"

    return _SENTINEL_RE.sub(replace, translated)


def round_trips(text: str) -> bool:
    """True if masking `text` and immediately restoring it is lossless.

    A self-check used by the extract stage to refuse pathological input before
    it reaches the model.
    """
    try:
        m = mask(text)
        return restore(m, m.text) == text
    except (MaskError, RoundTripError):
        return False
