"""Stable content hash for the translation cache.

Spec §6: "Cache by hash of the normalized source string so re-runs cost
nothing." The hash lives in the *cache* only. The emitted Lua tables are keyed
by the normalized string itself — see the note in SPEC.md §7 for why.

sha1 is chosen for length, not security: this is a content address, and the
input is public game text.
"""

import hashlib

from common.normalize import normalize


def cache_key(text: str, *, field: str = "") -> str:
    """Content address for a source string.

    `field` distinguishes otherwise-identical strings whose register differs by
    role — a quest *title* and a quest *objective* that happen to share wording
    should not share a translation.
    """
    payload = f"{field}\x00{normalize(text)}".encode()
    return hashlib.sha1(payload).hexdigest()[:16]
