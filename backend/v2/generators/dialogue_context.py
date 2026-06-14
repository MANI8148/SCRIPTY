"""Relationship-aware subtext and dialogue context.

Extracted from character_dialogue.py for standalone use by HybridGenerator.
"""

from __future__ import annotations

import random

_SUBTEXT_TEMPLATES: dict[str, list[str]] = {
    "inform": [
        "stating the obvious to buy time",
        "sharing information selectively",
        "pretending ignorance",
    ],
    "persuade": [
        "actually trying to convince themselves",
        "hiding uncertainty behind conviction",
        "manipulating through false concern",
    ],
    "deceive": [
        "hiding fear behind bravado",
        "protecting someone by lying",
        "testing the listener's knowledge",
    ],
    "threaten": [
        "bluffing with no real power",
        "revealing desperation through aggression",
        "establishing dominance out of insecurity",
    ],
    "comfort": [
        "avoiding the real issue",
        "deflecting from own guilt",
        "offering empty reassurance",
    ],
    "confess": [
        "seeking absolution more than understanding",
        "unburdening before it is too late",
        "testing trust through vulnerability",
    ],
    "question": [
        "already knows the answer",
        "fishing for confirmation of suspicions",
        "stalling for time to think",
    ],
    "command": [
        "asserting authority they do not have",
        "desperate for control",
        "testing obedience",
    ],
    "bargain": [
        "offering something they cannot deliver",
        "buying time with false promises",
        "desperate for any deal",
    ],
    "flirt": [
        "using charm as a weapon",
        "distracting from true intent",
        "testing attraction for leverage",
    ],
    "challenge": [
        "goading a reaction to reveal intentions",
        "asserting dominance",
        "hiding insecurity behind aggression",
    ],
    "warn": [
        "actually warning themselves",
        "testing if the other already knows",
        "hinting at hidden knowledge",
    ],
    "beg": [
        "hiding pride behind desperation",
        "genuinely at breaking point",
        "testing the other's mercy",
    ],
    "reveal": [
        "sharing a burden to create obligation",
        "confessing to gain trust",
        "unexpected moment of honesty",
    ],
}


def subtext_for_intent(intent_name: str) -> str:
    """Return a random subtext string for the given intent."""
    templates = _SUBTEXT_TEMPLATES.get(intent_name, ["speaking directly"])
    return random.choice(templates)
