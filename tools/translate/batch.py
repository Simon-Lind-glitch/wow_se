"""Message Batches submission, polling and result collection.

Batch rather than sync because this is the definition of a non-latency-sensitive
workload — it runs once per game patch on a developer's machine — and batch is
half price (spec §0: Anthropic API, Message Batches).
"""

import json
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

# Per-MTok list prices, halved by the batch discount at the point of use.
# Cached from the claude-api reference (2026-06-24); prices drift, so this is
# used for estimates and printed as an estimate, never billed against.
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
}
BATCH_DISCOUNT = 0.5

# Cheapest capable model, and the default: this corpus is short strings with a
# tightly specified output contract. Swap with --model for a quality pass.
DEFAULT_MODEL = "claude-haiku-4-5"

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


class BatchError(RuntimeError):
    pass


@dataclass
class Group:
    """One request: a set of same-field strings translated together."""

    custom_id: str
    field: str
    items: list[dict]
    system: list[dict]
    user: str

    def estimated_input_tokens(self) -> int:
        # ~3.5 chars/token for English prose. An estimate, clearly labelled as
        # one; the alternative is a count_tokens call per group, which needs the
        # network for a number we only use to print a cost.
        system_chars = sum(len(b["text"]) for b in self.system)
        return int((system_chars + len(self.user)) / 3.5)

    def max_tokens(self) -> int:
        source = sum(len(item["masked"]) for item in self.items)
        # Swedish runs longer than English, and the JSON envelope costs tokens.
        return max(1024, min(16000, int(source / 2) + 512 * len(self.items)))


def build_request(group: Group, model: str) -> Request:
    return Request(
        custom_id=group.custom_id,
        params=MessageCreateParamsNonStreaming(
            model=model,
            max_tokens=group.max_tokens(),
            system=group.system,
            messages=[{"role": "user", "content": group.user}],
        ),
    )


def estimate_cost(groups: list[Group], model: str) -> dict:
    price_in, price_out = PRICES.get(model, PRICES[DEFAULT_MODEL])
    tokens_in = sum(g.estimated_input_tokens() for g in groups)
    # Output is roughly the Swedish text plus JSON scaffolding.
    tokens_out = sum(int(sum(len(i["masked"]) for i in g.items) / 2.8) + 40 for g in groups)
    return {
        "model": model,
        "requests": len(groups),
        "strings": sum(len(g.items) for g in groups),
        "est_input_tokens": tokens_in,
        "est_output_tokens": tokens_out,
        "est_usd": round(
            (tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out) * BATCH_DISCOUNT, 2
        ),
        "note": "estimate only; token counts are approximated from character length",
    }


def parse_reply(text: str) -> dict[int, dict]:
    """Pull the translation map out of a model reply.

    Tolerant of a markdown fence, because that is the one deviation from "JSON
    only" that models still occasionally produce, and it is not worth a retry.
    """
    cleaned = _FENCE.sub("", text.strip())
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise BatchError(f"reply was not JSON: {exc}: {cleaned[:200]!r}") from exc
    entries = payload.get("translations")
    if not isinstance(entries, list):
        raise BatchError(f"reply has no 'translations' list: {cleaned[:200]!r}")
    out: dict[int, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict) or "i" not in entry or "sv" not in entry:
            continue
        try:
            out[int(entry["i"])] = entry
        except (TypeError, ValueError):
            continue
    return out


class Batcher:
    def __init__(self, model: str = DEFAULT_MODEL, *, poll_seconds: int = 30):
        self.client = anthropic.Anthropic()
        self.model = model
        self.poll_seconds = poll_seconds

    def run(self, groups: list[Group], *, on_status=None) -> dict[str, str]:
        """Submit, wait, and return {custom_id: reply text} for successes."""
        if not groups:
            return {}
        batch = self.client.messages.batches.create(
            requests=[build_request(g, self.model) for g in groups]
        )
        if on_status:
            on_status(f"batch {batch.id} submitted with {len(groups)} requests")

        while True:
            batch = self.client.messages.batches.retrieve(batch.id)
            if batch.processing_status == "ended":
                break
            if on_status:
                counts = batch.request_counts
                on_status(
                    f"batch {batch.id}: {batch.processing_status} "
                    f"(succeeded {counts.succeeded}, errored {counts.errored}, "
                    f"processing {counts.processing})"
                )
            time.sleep(self.poll_seconds)

        replies: dict[str, str] = {}
        failures: dict[str, str] = {}
        for result in self.client.messages.batches.results(batch.id):
            kind = result.result.type
            if kind == "succeeded":
                message = result.result.message
                replies[result.custom_id] = next(
                    (b.text for b in message.content if b.type == "text"), ""
                )
            elif kind == "errored":
                failures[result.custom_id] = str(result.result.error.type)
            else:
                failures[result.custom_id] = kind
        if failures and on_status:
            kinds = sorted(set(failures.values()))
            on_status(f"{len(failures)} request(s) did not succeed: {kinds}")
        return replies

    def translate_one(self, system: list[dict], user: str, max_tokens: int = 2048) -> str:
        """A single synchronous call, used only for retrying rejected strings.

        Retries are a handful of items; waiting on another batch cycle for them
        would add an hour to the build for a few cents' saving.
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return next((b.text for b in message.content if b.type == "text"), "")


def chunk(items: list[dict], *, max_items: int, max_chars: int) -> Iterator[list[dict]]:
    """Group strings into requests, bounded by count and by size."""
    current: list[dict] = []
    size = 0
    for item in items:
        length = len(item["masked"])
        if current and (len(current) >= max_items or size + length > max_chars):
            yield current
            current, size = [], 0
        current.append(item)
        size += length
    if current:
        yield current
