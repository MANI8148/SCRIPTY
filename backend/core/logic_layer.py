"""
SCRIPTY - Logic Layer (V4 - Strategic Narrative)
Ensures semantic consistency and manages role-specific narrative impacts.
"""
import random

class LogicLayer:
    OBJECT_TYPES = {
        "event": {
            "verbs": ["prevent", "disrupt", "survive", "investigate", "witness"],
            "examples": ["uprising", "protest", "royal procession", "flood", "secret assembly"]
        },
        "information": {
            "verbs": ["decode", "leak", "verify", "uncover", "hide", "expose"],
            "examples": ["ledger", "telegraph", "ancient manuscript", "diary", "record"]
        },
        "artifact": {
            "verbs": ["protect", "recover", "appraise", "smuggle", "safeguard"],
            "examples": ["relic", "heirloom", "ornament", "statue", "box"]
        },
        "conspiracy": {
            "verbs": ["foil", "unravel", "expose", "thwart"],
            "examples": ["plot", "scheme", "betrayal", "espionage"]
        }
    }

    ROLE_MOVES = {
        "clerk": {
            "specialty": "deciphering meticulous records and archived ledgers",
            "action_modifier": "examining the fine print of",
            "climax_move": "exposed the paper trail that led to"
        },
        "journalist": {
            "specialty": "following whispers and tracking leads that others missed",
            "action_modifier": "interviewing shadowy sources about",
            "climax_move": "published the damning evidence regarding"
        },
        "engineer": {
            "specialty": "analyzing structural weaknesses and technological systems",
            "action_modifier": "hacking into the primitive systems of",
            "climax_move": "disabled the mechanical traps surrounding"
        },
        "scholar": {
            "specialty": "translating dead languages and ancient symbols",
            "action_modifier": "studying the cryptic runes upon",
            "climax_move": "unlocked the deeper meaning within"
        },
        "detective": {
            "specialty": "connecting disparate clues and profiling motives",
            "action_modifier": "scrutinizing the crime scene for traces of",
            "climax_move": "confronted the culprit with the truth about"
        }
    }

    @classmethod
    def get_object_type(cls, obj_name: str) -> str:
        """Classifies an object name into a type with better defaults."""
        obj_lower = obj_name.lower()
        for obj_type, details in cls.OBJECT_TYPES.items():
            if any(example in obj_lower for example in details["examples"]):
                return obj_type
        # Heuristic: if it has 'manuscript' or 'ledger' it's information
        if "manuscript" in obj_lower or "ledger" in obj_lower:
            return "information"
        return "artifact"

    @classmethod
    def get_compatible_action(cls, obj_name: str) -> str:
        """Returns a semantically valid verb for a given object."""
        obj_type = cls.get_object_type(obj_name)
        verbs = cls.OBJECT_TYPES[obj_type]["verbs"]
        return random.choice(verbs)

    @classmethod
    def get_role_logic(cls, role_name: str) -> dict:
        """Returns the specific logic/strings for a character role."""
        role_key = role_name.lower()
        # Fallback to a generic role if not found
        if role_key not in cls.ROLE_MOVES:
            return {
                "specialty": "navigating the complexities of the city",
                "action_modifier": "investigating the nature of",
                "climax_move": "took a stand against the forces of"
            }
        return cls.ROLE_MOVES[role_key]

if __name__ == "__main__":
    test_obj = "ancient manuscript"
    print(f"Object: {test_obj}")
    print(f"Type: {LogicLayer.get_object_type(test_obj)}")
    print(f"Action: {LogicLayer.get_compatible_action(test_obj)}")
    print(f"Clerk Move: {LogicLayer.get_role_logic('clerk')['climax_move']}")
