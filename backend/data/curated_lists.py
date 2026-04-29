"""
Dataset Fallback / Curated Lists
Provide high-quality defaults for Characters, Roles, Conflicts, Locations, and Emotions.
"""

CHARACTERS = [
    "Arjun", "Aditya", "Ishaan", "Rohan", "Siddharth", "Vikram",
    "Ananya", "Diya", "Isha", "Meera", "Priya", "Sana",
    "Indra", "Karan", "Rahul", "Sameer", "Varun", "Zoya",
    "Ravi", "Anya", "Deepak", "Neha", "Kapil", "Kavya",
    "Mohit", "Nitin", "Anjali", "Sanjay", "Anushka", "Naveen"
]

ROLES = {
    "ancient": ["scholar", "royal guard", "merchant", "temple priest", "artisan", "astrologer"],
    "colonial": ["clerk", "detective", "revolutionary", "official", "journalist", "teacher"],
    "modern": ["engineer", "activist", "architect", "lawyer", "entrepreneur", "police officer"],
    "digital": ["data scientist", "cyber-security expert", "drone operator", "AI researcher", "system architect"]
}

EMOTIONS = [
    "apprehension", "determination", "curiosity", "despair", "hope",
    "vengeance", "ambition", "remorse", "exhaustion", "pride"
]

# Provide fallback lists for logic layer classification
CURATED_OBJECTS = {
    "Information": ["secret treaty", "hidden ledger", "ancient manuscript", "encrypted file", "scandalous photograph"],
    "Object": ["family heirloom", "stolen artifact", "royal dagger", "key to the vault", "mysterious package"],
    "Event": ["annual festival", "secret meeting", "midnight auction", "royal procession", "street protest"]
}

CURATED_LOCATIONS = {
    "rural": ["village square", "local well", "farmland", "old temple ruins", "riverbank"],
    "urban": ["bustling bazaar", "railway station", "historic fort", "clock tower", "public library"],
    "metro": ["glass skyscraper", "underground metro", "tech park plaza", "luxury cafe", "central traffic junction"]
}

CONFLICT_THEMES = [
    "betrayal",
    "forbidden knowledge",
    "fight for justice",
    "survival against nature",
    "political espionage",
    "protection of innocent",
    "uncovering the past"
]
