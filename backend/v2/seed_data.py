"""
SCRIPTY v2 — Seed Data
=====================
Reusable, real-world-flavoured data used to enrich generation: character
name pools by cultural background, trait libraries, genre/tone conventions,
dialogue openers, and location/era descriptors. Kept separate from logic so
it can be expanded without touching the engine.

All entries are plain data — no imports from the engine.
"""

from __future__ import annotations

from typing import Any

# ── Trait library (common literary personality traits) ──────────────────────
TRAIT_LIBRARY: list[str] = [
    "curious", "brave", "cautious", "deceptive", "kind", "ambitious",
    "loyal", "reckless", "wise", "pious", "spiritual", "rude", "brash",
    "gentle", "compassionate", "cunning", "sly", "proud", "anxious",
    "mysterious", "melancholic", "patient", "bitter", "hopeful", "charismatic",
    "stubborn", "generous", "envious", "vengeful", "optimistic", "pragmatic",
    "idealistic", "cynical", "honorable", "cruel", "timid", "bold",
    "reserved", "gregarious", "superstitious", "worldly", "naive", "jaded",
]

# Traits grouped by rough positive / negative / neutral valence.
TRAIT_VALENCE: dict[str, str] = {
    "curious": "positive", "brave": "positive", "kind": "positive",
    "loyal": "positive", "wise": "positive", "gentle": "positive",
    "compassionate": "positive", "pious": "positive", "spiritual": "positive",
    "patient": "positive", "hopeful": "positive", "generous": "positive",
    "optimistic": "positive", "honorable": "positive", "bold": "positive",
    "gregarious": "positive", "idealistic": "positive", "reserved": "neutral",
    "pragmatic": "neutral", "cautious": "neutral", "worldly": "neutral",
    "naive": "neutral", "mysterious": "neutral",
    "deceptive": "negative", "reckless": "negative", "rude": "negative",
    "brash": "negative", "sly": "negative", "proud": "negative",
    "anxious": "negative", "melancholic": "negative", "bitter": "negative",
    "envious": "negative", "vengeful": "negative", "cynical": "negative",
    "cruel": "negative", "timid": "negative", "stubborn": "neutral",
    "superstitious": "neutral", "jaded": "negative", "charismatic": "positive",
}

# ── Character name pools by cultural background ────────────────────────────
NAME_POOLS: dict[str, dict[str, list[str]]] = {
    "indian": {
        "male": ["Arjun", "Karan", "Ravi", "Vikram", "Dev", "Aditya", "Rohan",
                 "Arun", "Suresh", "Nikhil", "Yash", "Kabir", "Ishaan", "Vihaan"],
        "female": ["Maya", "Priya", "Ananya", "Kavya", "Divya", "Meera", "Sita",
                   "Aisha", "Leela", "Naina", "Tara", "Rhea", "Anjali", "Kira"],
    },
    "english": {
        "male": ["Arthur", "Edmund", "William", "Thomas", "Henry", "Robert",
                 "George", "Edward", "Richard", "Oliver", "Charles", "Hugh"],
        "female": ["Eleanor", "Margaret", "Alice", "Mary", "Jane", "Emma",
                   "Catherine", "Beatrice", "Rose", "Agnes", "Martha", "Clara"],
    },
    "french": {
        "male": ["Etienne", "Luc", "Henri", "Pierre", "Julien", "Gaston",
                 "Armand", "Marcel", "Philippe", "Renaud"],
        "female": ["Marguerite", "Colette", "Camille", "Elise", "Yvette",
                   "Simone", "Odette", "Genevieve", "Fleur", "Lucie"],
    },
    "arabic": {
        "male": ["Omar", "Idris", "Tariq", "Yusuf", "Khalid", "Rashid",
                 "Samir", "Zayd", "Faris", "Malik"],
        "female": ["Layla", "Zahra", "Amina", "Yasmin", "Salma", "Nadia",
                   "Leila", "Fatima", "Ranya", "Dalia"],
    },
    "japanese": {
        "male": ["Haru", "Kenji", "Takashi", "Ryo", "Sora", "Akira",
                 "Hiroshi", "Daichi", "Ren", "Yuki"],
        "female": ["Sakura", "Hana", "Yuki", "Aiko", "Mei", "Naomi",
                   "Rin", "Emi", "Kaori", "Tomoko"],
    },
    "russian": {
        "male": ["Dmitri", "Ivan", "Pavel", "Nikolai", "Alexei", "Vladimir",
                 "Boris", "Sergei", "Mikhail", "Fyodor"],
        "female": ["Anastasia", "Olga", "Tatiana", "Katya", "Irina",
                   "Natasha", "Ludmila", "Vera", "Masha", "Nina"],
    },
}

# ── Genre conventions: tone + typical settings + signature conflicts ────────
GENRE_CONVENTIONS: dict[str, dict[str, Any]] = {
    "historical_fiction": {
        "tone": "serious",
        "settings": ["bustling bazaar", "colonial courtroom", "dusty archive",
                     "rain-soaked street", "grand palace", "frontier outpost"],
        "conflicts": ["political intrigue", "colonial oppression",
                      "class divide", "family honour", "forbidden love"],
        "themes": ["freedom", "identity", "legacy", "resistance"],
    },
    "fantasy": {
        "tone": "epic",
        "settings": ["ancient forest", "crumbling tower", "mist-shrouded isle",
                     "forge of the dwarves", "capital of the realm", "cursed fen"],
        "conflicts": ["prophecy unfulfilled", "usurped throne",
                      "awakening evil", "forbidden magic", "warring houses"],
        "themes": ["destiny", "sacrifice", "power", "belonging"],
    },
    "mystery": {
        "tone": "tense",
        "settings": ["fog-bound manor", "smoke-filled office", "quiet library",
                     "train compartment", "rain-slick alley", "boardroom"],
        "conflicts": ["unsolved murder", "vanished heirloom",
                      "hidden will", "blackmail", "buried secret"],
        "themes": ["truth", "justice", "deception", "guilt"],
    },
    "romance": {
        "tone": "warm",
        "settings": ["coastal village", "bustling café", "country estate",
                     "city rooftop", "flower market", "quiet chapel"],
        "conflicts": ["misunderstanding", "rival suitor", "family objection",
                      "distance", "secret past"],
        "themes": ["love", "trust", "forgiveness", "home"],
    },
    "horror": {
        "tone": "grim",
        "settings": ["isolated village", "decaying mansion", "frozen pass",
                     "flooded basement", "misted moor", "abandoned sanatorium"],
        "conflicts": ["ancient curse", "unknown stalker", "possession",
                      "plague", "mass hysteria"],
        "themes": ["fear", "survival", "madness", "guilt"],
    },
    "science_fiction": {
        "tone": "tense",
        "settings": ["orbital station", "deserted colony", "megacity underdome",
                     "research vessel", "ruined terraform", "data sanctum"],
        "conflicts": ["ai revolt", "resource collapse", "first contact",
                      "tyrannical corp", "timeline fracture"],
        "themes": ["progress", "identity", "control", "humanity"],
    },
    "adventure": {
        "tone": "hopeful",
        "settings": ["uncharted jungle", "windswept harbour", "mountain pass",
                     "caravan route", "lost temple", "stormy strait"],
        "conflicts": ["treacherous terrain", "rival explorer", "betrayal",
                      "natural disaster", "impossible odds"],
        "themes": ["courage", "discovery", "freedom", "loyalty"],
    },
    "drama": {
        "tone": "intimate",
        "settings": ["family kitchen", "factory floor", "tenement stair",
                     "clinic waiting room", "schoolyard", "bus terminal"],
        "conflicts": ["generational rift", "economic strain", "illness",
                      "lost ambition", "reckoning"],
        "themes": ["family", "dignity", "choice", "time"],
    },
}

# ── Dialogue openers by intent (templates the realizer can draw from) ──────
DIALOGUE_OPENERS: dict[str, list[str]] = {
    "challenge": ["You call that courage?", "Stand and face me.",
                  "Do you threaten me, or merely boast?"],
    "comfort": ["It will be all right, you'll see.", "Breathe. We are still here.",
                "You are not alone in this."],
    "deceive": ["Nothing is amiss, I assure you.", "You misheard, that is all.",
                "Trust me — I have it handled."],
    "threaten": ["One more step and you'll regret it.", "I will not warn you twice.",
                 "This ends tonight."],
    "question": ["What did you mean by that?", "Where were you, really?",
                 "You knew, didn't you?"],
    "persuade": ["Listen — there is another way.", "We can still fix this.",
                 "Think of what we stand to lose."],
    "inform": ["I learned something in the market.", "The letter arrived at dawn.",
               "They are moving against us."],
    "reveal": ["I have carried this too long.", "The truth is simpler, and worse.",
               "It was me. All along."],
    "command": ["Hold the line. No retreat.", "Do as I say, now.",
                "Quiet — both of you."],
}

# ── Era descriptors by century-ish bucket (used when no explicit setting) ───
ERA_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "ancient": {
        "tech_level": "bronze",
        "infrastructure": ["mud-brick walls", "stone aqueducts", "open forums"],
        "transport": ["foot", "donkey", "river barge"],
        "tone": "epic",
    },
    "medieval": {
        "tech_level": "pre-industrial",
        "infrastructure": ["castle walls", "cobbled squares", "wooden piers"],
        "transport": ["horse", "cart", "walking"],
        "tone": "serious",
    },
    "colonial": {
        "tech_level": "industrial",
        "infrastructure": ["railways", "telegraph lines", "civic halls"],
        "transport": ["train", "horse carriage", "steamer"],
        "tone": "serious",
    },
    "modern": {
        "tech_level": "digital",
        "infrastructure": ["skyscrapers", "subways", "fiber networks"],
        "transport": ["metro", "car", "aircraft"],
        "tone": "tense",
    },
    "future": {
        "tech_level": "post-digital",
        "infrastructure": ["arcologies", "orbital lifts", "smart grids"],
        "transport": ["maglev", "aircar", "telepresence"],
        "tone": "tense",
    },
}


def name_pool(culture: str, gender: str) -> list[str]:
    """Return a name list for a culture/gender, or a sensible default."""
    pool = NAME_POOLS.get(culture.lower())
    if pool is None:
        # Fall back to the union of all pools for that gender.
        gender = gender.lower()
        out: list[str] = []
        for p in NAME_POOLS.values():
            out.extend(p.get(gender, []))
        return out
    return pool.get(gender.lower(), pool.get("male", []))


def genre_convention(genre: str) -> dict[str, Any]:
    """Return convention dict for a genre, or historical_fiction default."""
    return GENRE_CONVENTIONS.get(genre.lower(), GENRE_CONVENTIONS["historical_fiction"])


def era_descriptor(era: str) -> dict[str, Any]:
    """Return era descriptor, defaulting to modern."""
    return ERA_DESCRIPTORS.get(era.lower(), ERA_DESCRIPTORS["modern"])
