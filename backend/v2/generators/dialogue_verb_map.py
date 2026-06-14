"""Intent -> dialogue verb mapping extracted from character_dialogue.py."""

from __future__ import annotations

import random

_INTENT_VERBS: dict[str, list[str]] = {
    "inform": ["said", "explained", "mentioned", "noted", "stated", "replied"],
    "persuade": ["urged", "argued", "implored", "insisted", "pressed", "contended"],
    "deceive": ["lied", "deflected", "fibbed", "dissembled", "prevaricated"],
    "threaten": ["hissed", "snarled", "threatened", "warned", "vowed", "spat"],
    "comfort": ["soothed", "reassured", "consoled", "comforted", "gentled"],
    "confess": ["whispered", "admitted", "confessed", "breathed", "conceded"],
    "question": ["asked", "inquired", "demanded", "probed", "queried", "pressed"],
    "command": ["ordered", "commanded", "directed", "instructed", "barked"],
    "bargain": ["offered", "proposed", "negotiated", "countered", "bargained"],
    "flirt": ["teased", "purred", "cooed", "flirted", "breathed"],
    "challenge": ["challenged", "goaded", "taunted", "provoked", "dared"],
    "warn": ["cautioned", "warned", "alerted", "advised", "counseled"],
    "beg": ["pleaded", "begged", "implored", "beseeched", "entreated"],
    "reveal": ["revealed", "disclosed", "unveiled", "confided", "divulged"],
}


def verb_for_intent(intent_name: str) -> str:
    """Return a random dialogue verb for the given intent."""
    verbs = _INTENT_VERBS.get(intent_name, ["said"])
    return random.choice(verbs)
