from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional


class Category(Enum):
    DIALOGUE = "dialogue"
    DIALOGUE_SUBTEXT = "dialogue_subtext"
    DIALOGUE_CONFESSIONS = "dialogue_confessions"
    DIALOGUE_ARGUMENTS = "dialogue_arguments"
    DIALOGUE_THREATS = "dialogue_threats"
    DIALOGUE_FLIRTATION = "dialogue_flirtation"
    DIALOGUE_NEGOTIATION = "dialogue_negotiation"
    BODY_LANGUAGE = "body_language"
    MICROEXPRESSIONS = "microexpressions"
    FACIAL_EXPRESSIONS = "facial_expressions"
    GESTURES = "gestures"
    MOVEMENT_PATTERNS = "movement_patterns"
    ACTIONS = "actions"
    PHYSICAL_ACTIONS = "physical_actions"
    GOAL_DRIVEN_ACTIONS = "goal_driven_actions"
    INVESTIGATION_ACTIONS = "investigation_actions"
    COMBAT_ACTIONS = "combat_actions"
    SOCIAL_ACTIONS = "social_actions"
    REACTIONS = "reactions"
    EMOTIONAL_REACTIONS = "emotional_reactions"
    PHYSICAL_REACTIONS = "physical_reactions"
    SOCIAL_REACTIONS = "social_reactions"
    CONFLICTS = "conflicts"
    INTERNAL_CONFLICTS = "internal_conflicts"
    INTERPERSONAL_CONFLICTS = "interpersonal_conflicts"
    GROUP_CONFLICTS = "group_conflicts"
    INSTITUTIONAL_CONFLICTS = "institutional_conflicts"
    MORAL_CONFLICTS = "moral_conflicts"
    RELATIONSHIPS = "relationships"
    FRIENDSHIPS = "friendships"
    RIVALRIES = "rivalries"
    ROMANCES = "romances"
    FAMILY_RELATIONSHIPS = "family_relationships"
    MENTOR_RELATIONSHIPS = "mentor_relationships"
    BETRAYALS = "betrayals"
    MEMORIES = "memories"
    FLASHBACKS = "flashbacks"
    TRAUMA_MEMORIES = "trauma_memories"
    NOSTALGIC_MEMORIES = "nostalgic_memories"
    REGRET_MEMORIES = "regret_memories"
    VICTORY_MEMORIES = "victory_memories"
    SCENE_OPENINGS = "scene_openings"
    SCENE_ENDINGS = "scene_endings"
    SCENE_HOOKS = "scene_hooks"
    SCENE_TURNING_POINTS = "scene_turning_points"
    SCENE_REVELATIONS = "scene_revelations"
    SCENE_CLIFFHANGERS = "scene_cliffhangers"
    SENSORY_DETAILS = "sensory_details"
    VISUAL = "visual"
    AUDITORY = "auditory"
    OLFACTORY = "olfactory"
    TACTILE = "tactile"
    GUSTATORY = "gustatory"
    CHARACTER_THOUGHTS = "character_thoughts"
    BELIEFS = "beliefs"
    GOALS = "goals"
    INTENTIONS = "intentions"
    MOTIVATIONS = "motivations"
    FEARS = "fears"
    DESIRES = "desires"
    EMOTIONS = "emotions"
    ANGER = "anger"
    FEAR = "fear"
    JOY = "joy"
    SADNESS = "sadness"
    GUILT = "guilt"
    SHAME = "shame"
    JEALOUSY = "jealousy"
    HOPE = "hope"
    DESPERATION = "desperation"
    WORLDBUILDING = "worldbuilding"
    LOCATION_DESCRIPTIONS = "location_descriptions"
    CITY_DESCRIPTIONS = "city_descriptions"
    NATURE_DESCRIPTIONS = "nature_descriptions"
    HISTORICAL_CONTEXT = "historical_context"
    TECHNOLOGY_DESCRIPTIONS = "technology_descriptions"
    OCCUPATIONS = "occupations"
    LEADERS = "leaders"
    SOLDIERS = "soldiers"
    DETECTIVES = "detectives"
    CRIMINALS = "criminals"
    MERCHANTS = "merchants"
    POLITICIANS = "politicians"
    STUDENTS = "students"
    SCIENTISTS = "scientists"
    GENRE_PATTERNS = "genre_patterns"
    MYSTERY = "mystery"
    THRILLER = "thriller"
    ROMANCE = "romance"
    FANTASY = "fantasy"
    SCIENCE_FICTION = "science_fiction"
    LITERARY = "literary"
    HISTORICAL = "historical"
    HORROR = "horror"
    NARRATIVE_DEVICES = "narrative_devices"
    FORESHADOWING = "foreshadowing"
    SETUPS = "setups"
    PAYOFFS = "payoffs"
    RED_HERRINGS = "red_herrings"
    MISDIRECTION = "misdirection"
    CALLBACKS = "callbacks"
    SYMBOLISM = "symbolism"
    STORY_EVENTS = "story_events"
    DISCOVERIES = "discoveries"
    REVELATIONS = "revelations"
    CONFRONTATIONS = "confrontations"
    ESCAPES = "escapes"
    DEATHS = "deaths"
    VICTORIES = "victories"
    DEFEATS = "defeats"


CATEGORY_META = {
    Category.DIALOGUE: {"group": "dialogue", "weight": 0.8},
    Category.DIALOGUE_SUBTEXT: {"group": "dialogue", "weight": 0.9},
    Category.DIALOGUE_CONFESSIONS: {"group": "dialogue", "weight": 0.95},
    Category.DIALOGUE_ARGUMENTS: {"group": "dialogue", "weight": 0.85},
    Category.DIALOGUE_THREATS: {"group": "dialogue", "weight": 0.8},
    Category.DIALOGUE_FLIRTATION: {"group": "dialogue", "weight": 0.8},
    Category.DIALOGUE_NEGOTIATION: {"group": "dialogue", "weight": 0.85},
    Category.MICROEXPRESSIONS: {"group": "body_language", "weight": 0.95},
    Category.FACIAL_EXPRESSIONS: {"group": "body_language", "weight": 0.85},
    Category.GESTURES: {"group": "body_language", "weight": 0.8},
    Category.MOVEMENT_PATTERNS: {"group": "body_language", "weight": 0.8},
    Category.PHYSICAL_ACTIONS: {"group": "actions", "weight": 0.75},
    Category.GOAL_DRIVEN_ACTIONS: {"group": "actions", "weight": 0.9},
    Category.INVESTIGATION_ACTIONS: {"group": "actions", "weight": 0.85},
    Category.COMBAT_ACTIONS: {"group": "actions", "weight": 0.8},
    Category.SOCIAL_ACTIONS: {"group": "actions", "weight": 0.8},
    Category.EMOTIONAL_REACTIONS: {"group": "reactions", "weight": 0.85},
    Category.PHYSICAL_REACTIONS: {"group": "reactions", "weight": 0.8},
    Category.SOCIAL_REACTIONS: {"group": "reactions", "weight": 0.8},
    Category.INTERNAL_CONFLICTS: {"group": "conflicts", "weight": 0.9},
    Category.INTERPERSONAL_CONFLICTS: {"group": "conflicts", "weight": 0.85},
    Category.GROUP_CONFLICTS: {"group": "conflicts", "weight": 0.8},
    Category.INSTITUTIONAL_CONFLICTS: {"group": "conflicts", "weight": 0.85},
    Category.MORAL_CONFLICTS: {"group": "conflicts", "weight": 0.95},
    Category.FRIENDSHIPS: {"group": "relationships", "weight": 0.8},
    Category.RIVALRIES: {"group": "relationships", "weight": 0.85},
    Category.ROMANCES: {"group": "relationships", "weight": 0.85},
    Category.FAMILY_RELATIONSHIPS: {"group": "relationships", "weight": 0.8},
    Category.MENTOR_RELATIONSHIPS: {"group": "relationships", "weight": 0.8},
    Category.BETRAYALS: {"group": "relationships", "weight": 0.95},
    Category.FLASHBACKS: {"group": "memories", "weight": 0.85},
    Category.TRAUMA_MEMORIES: {"group": "memories", "weight": 0.9},
    Category.NOSTALGIC_MEMORIES: {"group": "memories", "weight": 0.8},
    Category.REGRET_MEMORIES: {"group": "memories", "weight": 0.85},
    Category.VICTORY_MEMORIES: {"group": "memories", "weight": 0.8},
    Category.SCENE_OPENINGS: {"group": "scene_patterns", "weight": 0.75},
    Category.SCENE_ENDINGS: {"group": "scene_patterns", "weight": 0.75},
    Category.SCENE_HOOKS: {"group": "scene_patterns", "weight": 0.85},
    Category.SCENE_TURNING_POINTS: {"group": "scene_patterns", "weight": 0.9},
    Category.SCENE_REVELATIONS: {"group": "scene_patterns", "weight": 0.9},
    Category.SCENE_CLIFFHANGERS: {"group": "scene_patterns", "weight": 0.85},
    Category.VISUAL: {"group": "sensory", "weight": 0.8},
    Category.AUDITORY: {"group": "sensory", "weight": 0.8},
    Category.OLFACTORY: {"group": "sensory", "weight": 0.85},
    Category.TACTILE: {"group": "sensory", "weight": 0.8},
    Category.GUSTATORY: {"group": "sensory", "weight": 0.85},
    Category.BELIEFS: {"group": "thoughts", "weight": 0.9},
    Category.GOALS: {"group": "thoughts", "weight": 0.85},
    Category.INTENTIONS: {"group": "thoughts", "weight": 0.85},
    Category.MOTIVATIONS: {"group": "thoughts", "weight": 0.9},
    Category.FEARS: {"group": "thoughts", "weight": 0.85},
    Category.DESIRES: {"group": "thoughts", "weight": 0.85},
    Category.ANGER: {"group": "emotions", "weight": 0.8},
    Category.FEAR: {"group": "emotions", "weight": 0.8},
    Category.JOY: {"group": "emotions", "weight": 0.8},
    Category.SADNESS: {"group": "emotions", "weight": 0.8},
    Category.GUILT: {"group": "emotions", "weight": 0.85},
    Category.SHAME: {"group": "emotions", "weight": 0.85},
    Category.JEALOUSY: {"group": "emotions", "weight": 0.85},
    Category.HOPE: {"group": "emotions", "weight": 0.8},
    Category.DESPERATION: {"group": "emotions", "weight": 0.85},
    Category.LOCATION_DESCRIPTIONS: {"group": "worldbuilding", "weight": 0.75},
    Category.CITY_DESCRIPTIONS: {"group": "worldbuilding", "weight": 0.75},
    Category.NATURE_DESCRIPTIONS: {"group": "worldbuilding", "weight": 0.75},
    Category.HISTORICAL_CONTEXT: {"group": "worldbuilding", "weight": 0.8},
    Category.TECHNOLOGY_DESCRIPTIONS: {"group": "worldbuilding", "weight": 0.75},
    Category.LEADERS: {"group": "occupations", "weight": 0.8},
    Category.SOLDIERS: {"group": "occupations", "weight": 0.8},
    Category.DETECTIVES: {"group": "occupations", "weight": 0.85},
    Category.CRIMINALS: {"group": "occupations", "weight": 0.8},
    Category.MERCHANTS: {"group": "occupations", "weight": 0.75},
    Category.POLITICIANS: {"group": "occupations", "weight": 0.8},
    Category.STUDENTS: {"group": "occupations", "weight": 0.75},
    Category.SCIENTISTS: {"group": "occupations", "weight": 0.8},
    Category.MYSTERY: {"group": "genre", "weight": 0.85},
    Category.THRILLER: {"group": "genre", "weight": 0.85},
    Category.ROMANCE: {"group": "genre", "weight": 0.85},
    Category.FANTASY: {"group": "genre", "weight": 0.85},
    Category.SCIENCE_FICTION: {"group": "genre", "weight": 0.85},
    Category.LITERARY: {"group": "genre", "weight": 0.85},
    Category.HISTORICAL: {"group": "genre", "weight": 0.85},
    Category.HORROR: {"group": "genre", "weight": 0.85},
    Category.FORESHADOWING: {"group": "narrative_devices", "weight": 0.9},
    Category.SETUPS: {"group": "narrative_devices", "weight": 0.85},
    Category.PAYOFFS: {"group": "narrative_devices", "weight": 0.9},
    Category.RED_HERRINGS: {"group": "narrative_devices", "weight": 0.85},
    Category.MISDIRECTION: {"group": "narrative_devices", "weight": 0.85},
    Category.CALLBACKS: {"group": "narrative_devices", "weight": 0.85},
    Category.SYMBOLISM: {"group": "narrative_devices", "weight": 0.9},
    Category.DISCOVERIES: {"group": "story_events", "weight": 0.85},
    Category.REVELATIONS: {"group": "story_events", "weight": 0.9},
    Category.CONFRONTATIONS: {"group": "story_events", "weight": 0.85},
    Category.ESCAPES: {"group": "story_events", "weight": 0.8},
    Category.DEATHS: {"group": "story_events", "weight": 0.85},
    Category.VICTORIES: {"group": "story_events", "weight": 0.8},
    Category.DEFEATS: {"group": "story_events", "weight": 0.8},
}


EMOTION_KEYWORDS = {
    "anger": {"angry", "furious", "enraged", "irate", "seething", "livid", "wrathful", "indignant", "outraged", "annoyed", "irritated", "frustrated", "hostile"},
    "fear": {"afraid", "scared", "terrified", "frightened", "panicked", "petrified", "horrified", "anxious", "dread", "nervous", "worried", "apprehensive", "paranoid"},
    "joy": {"happy", "joyful", "delighted", "elated", "ecstatic", "thrilled", "overjoyed", "gleeful", "cheerful", "content", "pleased", "exuberant"},
    "sadness": {"sad", "unhappy", "depressed", "miserable", "heartbroken", "devastated", "grief", "sorrow", "despondent", "melancholy", "mournful", "somber"},
    "guilt": {"guilty", "remorseful", "contrite", "apologetic", "regretful", "ashamed", "culpable", "blameworthy"},
    "shame": {"ashamed", "humiliated", "embarrassed", "mortified", "disgraced", "degraded", "shamefaced"},
    "jealousy": {"jealous", "envious", "covetous", "resentful", "possessive", "begrudging", "green-eyed"},
    "hope": {"hopeful", "optimistic", "expectant", "aspiring", "confident", "wishful", "buoyant"},
    "desperation": {"desperate", "frantic", "anguished", "distraught", "despairing", "hopeless", "agonized", "vulnerable"},
}

GENRE_KEYWORDS = {
    "mystery": {"murder", "detective", "clue", "investigation", "suspect", "alibi", "mystery", "whodunit", "sleuth", "evidence"},
    "thriller": {"chase", "pursuit", "conspiracy", "hostage", "suspense", "terrorist", "assassin", "thriller", "manhunt", "countdown"},
    "romance": {"love", "romance", "passion", "kiss", "embrace", "romantic", "heart", "desire", "yearning", "intimacy"},
    "fantasy": {"magic", "dragon", "sword", "spell", "wizard", "kingdom", "quest", "enchanted", "mythical", "sorcery"},
    "science_fiction": {"spaceship", "alien", "robot", "future", "cyber", "quantum", "dimension", "starship", "artificial", "genetic"},
    "literary": {"existential", "consciousness", "society", "identity", "alienation", "modernist", "metaphor", "prose"},
    "historical": {"king", "queen", "battle", "empire", "century", "medieval", "ancient", "revolution", "war", "dynasty"},
    "horror": {"haunted", "ghost", "monster", "scream", "blood", "darkness", "curse", "demon", "undead", "terrifying"},
}

SCENE_ROLES = {"opening", "rising_action", "climax", "falling_action", "resolution", "turning_point", "flashback", "setup", "payoff"}
NARRATIVE_FUNCTIONS = {"exposition", "conflict_escalation", "character_development", "worldbuilding", "plot_advancement", "tension_building", "revelation", "relief", "thematic"}


def get_category_metadata(category: Category) -> dict:
    return CATEGORY_META.get(category, {"group": "other", "weight": 0.5})


def get_group(category: Category) -> str:
    return get_category_metadata(category)["group"]
