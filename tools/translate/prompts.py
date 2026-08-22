"""The translation prompt.

Spec §6: "Pass these to the model as system-level instruction, not as a
suffix." So the rules live in the system block — which also makes the block
byte-identical across every request in a run, so prompt caching actually hits.
The per-request user message carries only the strings.
"""

import json

from common.glossary import load as load_glossary

READING_AGE = 9

_RULES = f"""\
You translate World of Warcraft game text from English into Swedish.

THE READER
The reader is a Swedish child, about {READING_AGE} years old, who does not read
English. They are playing the game right now and need to understand what to do.

- Short sentences. Everyday spoken Swedish, the words a {READING_AGE}-year-old
  actually uses.
- Clarity beats literary fidelity. If the English is ornate or archaic, say the
  same thing plainly. If an English sentence is long, split it.
- Tone: adventurous and warm. This is a game, not a manual. Do not sound
  bureaucratic and do not talk down to the reader.
- Use "du" for the player, never "ni" or "Ni".

PROPER NOUNS STAY IN ENGLISH
Never translate the name of a person, place, creature, item, spell, or quest
giver. Keep them exactly as written, including apostrophes: Gornek, Durotar,
Valley of Trials, Mottled Boar, Hearthstone.
This is deliberate: the child must still be able to follow an English guide,
search the web, and talk to other players. Inflect around the name instead of
translating it ("Gorneks order", "till Razor Hill").

PLACEHOLDERS — THE HARD RULE
Some text contains machine tokens written as [[0]], [[1]], [[2]].
These are not words. They are format specifiers and game variables that the
game replaces at runtime.

- Reproduce every placeholder exactly, with the same digits.
- Use each one exactly once. Never add one that was not in the input.
- Keep non-positional ones in the same relative order as the input.
- Never translate, renumber, reformat, or put spaces inside them.

A wrong placeholder is a crash in a child's game, not a stylistic slip. If you
cannot fit a placeholder into natural Swedish, choose more awkward Swedish and
keep the placeholder.

STRUCTURE
Preserve paragraph breaks and blank lines as they appear in the input. Do not
add greetings, notes, explanations, or quotation marks that were not there.

OUTPUT FORMAT
Reply with JSON only. No prose before or after, no markdown fences.

{{"translations": [{{"i": <the item's i>, "sv": "<the Swedish text>"}}]}}

Return exactly one entry per input item, with the same "i" value. If an item
carries "gender_branches", add a "gender" key to that entry: a list of
[male, female] Swedish pairs, one per branch, in the same order. Translate each
branch as it would read in a finished sentence — Swedish adjective and noun
agreement does not line up with English, so translate the branches, do not copy
them.
"""

_FIELD_NOTES = {
    "ui": (
        "These are interface labels: buttons, tabs, tooltips, error messages. "
        "Keep them very short — they sit in fixed-width buttons and panels. "
        "A label is not a sentence: no trailing full stop unless the English has one."
    ),
    "quest.title": (
        "These are quest titles shown in a list. Short, punchy, no trailing full stop."
    ),
    "quest.objectives": (
        "These are quest objectives — the single most important text in the game for this "
        "reader, because it says what to actually do. Be concrete and unambiguous. "
        "Keep numbers exactly as written."
    ),
    "quest.description": (
        "This is what a quest giver says when offering the quest. It may be long and "
        "flowery in English. Keep the story, simplify the language."
    ),
    "quest.progress": ("This is what the quest giver says when the player returns unfinished."),
    "quest.completion": ("This is what the quest giver says on handing in the quest."),
}


def system_prompt(field: str) -> list[dict]:
    """System blocks for a group of same-field strings.

    Two blocks: the invariant rules plus glossary (cached), then a short note on
    the field. Splitting them keeps the cacheable prefix identical across every
    request in the run regardless of which field a group holds.
    """
    glossary = load_glossary()
    return [
        {
            "type": "text",
            "text": f"{_RULES}\n\n{glossary.prompt_block()}",
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": _FIELD_NOTES.get(field, _FIELD_NOTES["ui"])},
    ]


def user_message(items: list[dict]) -> str:
    """The per-request payload: just the strings, as JSON."""
    payload = []
    for item in items:
        entry = {"i": item["i"], "en": item["masked"]}
        if item.get("gender_branches"):
            entry["gender_branches"] = item["gender_branches"]
        payload.append(entry)
    return json.dumps({"items": payload}, ensure_ascii=False, indent=1)


def retry_message(item: dict, problems: list[str]) -> str:
    """A single-item retry that names what was wrong with the last attempt.

    Naming the specific placeholder is the difference between a retry that
    fixes it and a retry that makes the same mistake.
    """
    faults = "\n".join(f"- {p}" for p in problems)
    return json.dumps(
        {
            "items": [
                {
                    "i": item["i"],
                    "en": item["masked"],
                    **(
                        {"gender_branches": item["gender_branches"]}
                        if item.get("gender_branches")
                        else {}
                    ),
                }
            ],
            "previous_attempt_was_rejected": faults,
            "instruction": (
                "Your previous translation of this item was rejected for the reason above. "
                "Translate it again and get the placeholders exactly right."
            ),
        },
        ensure_ascii=False,
        indent=1,
    )
