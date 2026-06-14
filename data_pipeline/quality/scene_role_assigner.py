"""
Scene Role Assigner Module

Classifies scenes into roles: opening, rising_action, climax, turning_point,
resolution, revelation, setup, cliffhanger, falling_action.

Uses position in chapter, tension levels, emotion intensity, narrative function,
and text pattern matching to assign scene roles.
"""

from typing import List, Dict, Optional
import re
import logging
from collections import Counter, defaultdict

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import SCENE_ROLES, NARRATIVE_FUNCTIONS


logger = logging.getLogger(__name__)


# Opening indicators
OPENING_INDICATORS = [
    r'^the\s+', r'^it\s+was\b', r'^there\s+was\b', r'^there\s+were\b',
    r'^once\b', r'^in\s+the\b', r'^a\s+', r'^an\s+',
    r'^this\s+', r'^that\s+', r'^these\s+', r'^those\s+',
    r'^his\s+', r'^her\s+', r'^their\s+', r'^our\s+',
    r'^when\b', r'^as\b', r'^after\b', r'^before\b',
    r'^it\s+had\s+been\b', r'^it\s+was\s+a\b', r'^the\s+sun\b',
    r'^morning\b', r'^night\b', r'^evening\b', r'^day\b',
    r'^at\s+', r'^from\s+', r'^by\s+', r'^with\s+',
]

# Rising action indicators (scene builds tension)
RISING_ACTION_INDICATORS = [
    r'\bmeanwhile\b', r'\blater\b', r'\bthe\s+next\b',
    r'\bafter\s+that\b', r'\bthen\b', r'\bnext\b',
    r'\bgradually\b', r'\bslowly\b', r'\bstey\s+by\s+step\b',
    r'\bincreasingly\b', r'\bgrowing\b', r'\bmounting\b',
    r'\bcontinued\b', r'\bproceeded\b', r'\badvanced\b',
    r'\bfurther\b', r'\bdeeper\b', r'\bfarther\b',
    r'\bapproached\b', r'\bdrew\s+closer\b',
    r'\bpreparing\b', r'\bplanning\b', r'\bgetting\s+ready\b',
]

# Climax indicators (peak tension, sudden events)
CLIMAX_INDICATORS = [
    r'\bsuddenly\b', r'\babruptly\b', r'\bwithout\s+warning\b',
    r'\ball\s+at\s+once\b', r'\bout\s+of\s+nowhere\b',
    r'\bin\s+that\s+instant\b', r'\bin\s+that\s+moment\b',
    r'\bat\s+that\s+moment\b', r'\bright\s+then\b',
    r'\bexplosion\b', r'\bscream(?:ed|ing)?\b', r'\bshout(?:ed|ing)?\b',
    r'\bcrash(?:ed|ing)?\b', r'\battack(?:ed|ing)?\b',
    r'\bimpact\b', r'\bcrisis\b', r'\bclimax\b',
    r'\bdesperate\b', r'\bfrantic\b', r'\bpanic(?:ked)?\b',
    r'\bcharged\b', r'\brushed\b', r'\blunged\b',
    r'\bin\s+the\s+nick\s+of\s+time\b', r'\bjust\s+in\s+time\b',
]

# Turning point indicators (revelation, change of direction)
TURNING_POINT_INDICATORS = [
    r'\bsuddenly\s+(?:realized?|understood?|knew)\b',
    r'\bin\s+that\s+moment\b', r'\bat\s+that\s+instant\b',
    r'\beverything\s+changed\b', r'\bnothing\s+would\s+be\s+the\s+same\b',
    r'\ba\s+turning\s+point\b', r'\ba\s+shift\b',
    r'\ba\s+change\b', r'\bbut\s+then\b', r'\bhowever\b',
    r'\byet\b.*\bsuddenly\b', r'\bthough\b.*\brealized?\b',
    r'\bdiscover(?:ed|y)?\b', r'\breveal(?:ed|ation)?\b',
    r'\btruth\b', r'\bsecret\b.*\brevealed?\b',
    r'\bthe\s+truth\b', r'\bsaw\s+the\s+truth\b',
]

# Resolution indicators
RESOLUTION_INDICATORS = [
    r'\bfinally\b', r'\bat\s+last\b', r'\bin\s+the\s+end\b',
    r'\band\s+so\b', r'\bthus\s+it\s+was\b',
    r'\ball\s+was\b', r'\beverything\s+was\b',
    r'\bpeace(?:ful)?\b', r'\bcalm(?:ed|ly)?\b',
    r'\bquiet(?:ly|er)?\b', r'\brest(?:ed|ing)?\b',
    r'\bsettled\b', r'\bresolved?\b', r'\baccepted\b',
    r'\bended\b', r'\bconcluded\b', r'\bfinished\b',
    r'\bthe\s+end\b', r'\bend\b', r'\bfinal\b',
]

# Revelation indicators
REVELATION_INDICATORS = [
    r'\breveal(?:ed|ation)?\b', r'\bdiscover(?:ed|y)?\b',
    r'\bfind\s+out\b', r'\blearn(?:ed)?\s+the\s+truth\b',
    r'\bshock(?:ed|ing)?\b', r'\brealiz(?:ed|ation)?\b',
    r'\bexpose(?:d)?\b', r'\buncover(?:ed)?\b',
    r'\bemerged?\b', r'\bcame\s+to\s+light\b',
    r'\bshow(?:ed|n)?\s+the\s+truth\b',
    r'\bthe\s+truth\s+was\b', r'\blay\s+bare\b',
    r'\brevealed?\s+itself\b',
]

# Setup indicators
SETUP_INDICATORS = [
    r'\bif\s+only\b', r'\bhad\s+(?:he|she|they)\s+known\b',
    r'\blittle\s+did\b', r'\bwhat\s+he\s+didn\'?t\s+know\b',
    r'\bwhat\s+she\s+didn\'?t\s+know\b', r'\bunaware\b',
    r'\bunknowingly\b', r'\bunbeknownst\b',
    r'\blater\s+would\b', r'\bwould\s+later\b',
    r'\bthis\s+was\s+the\s+moment\b', r'\bthis\s+would\b',
    r'\bseeds?\s+of\b', r'\bpremonition\b',
    r'\bomen\b', r'\bforeboding\b',
]

# Cliffhanger indicators
CLIFFHANGER_INDICATORS = [
    r'\bto\s+be\s+continued\b', r'\bcliffhanger\b',
    r'\bwhat\s+would\b', r'\bwould\s+they\b',
    r'\blittle\s+did\s+they\s+know\b',
    r'\band\s+then\b.*\.\.\.', r'\b\.\.\.\b',
    r'\bto\s+be\s+continued\.\.\.\b',
    r'\bsuddenly\s+the\s+door\s+flew\s+open\b',
    r'\bthe\s+silence\s+was\s+broken\b',
    r'\ba\s+figure\b', r'\ba\s+voice\b',
    r'\bwhat\s+happened\s+next\b',
]

# Falling action indicators
FALLING_ACTION_INDICATORS = [
    r'\baftermath\b', r'\bin\s+the\s+wake\b',
    r'\bthe\s+dust\s+settled\b', r'\bthe\s+silence\b',
    r'\bcaught\s+their\s+breath\b', r'\bgasp(?:ed|ing)?\b',
    r'\btrying\s+to\s+understand\b', r'\bprocess\s+what\b',
    r'\bconsequences\b', r'\bresults?\b',
    r'\bimplications\b', r'\brepercussions\b',
    r'\bwhat\s+had\s+happened\b', r'\bsank\s+in\b',
    r'\bdawning\s+realization\b', r'\bthe\s+meaning\b',
]


class SceneRoleAssigner:
    """Assigns scene roles to NarrativeFragment based on text analysis."""

    def __init__(self):
        self.opening_patterns = [re.compile(p) for p in OPENING_INDICATORS]
        self.rising_action_patterns = [re.compile(p) for p in RISING_ACTION_INDICATORS]
        self.climax_patterns = [re.compile(p) for p in CLIMAX_INDICATORS]
        self.turning_point_patterns = [re.compile(p) for p in TURNING_POINT_INDICATORS]
        self.resolution_patterns = [re.compile(p) for p in RESOLUTION_INDICATORS]
        self.revelation_patterns = [re.compile(p) for p in REVELATION_INDICATORS]
        self.setup_patterns = [re.compile(p) for p in SETUP_INDICATORS]
        self.cliffhanger_patterns = [re.compile(p) for p in CLIFFHANGER_INDICATORS]
        self.falling_action_patterns = [re.compile(p) for p in FALLING_ACTION_INDICATORS]
        self.stats = {
            "fragments_processed": 0,
            "roles_assigned": 0,
            "existing_kept": 0,
            "by_role": Counter(),
        }

        self._pattern_map = [
            ("climax", self.climax_patterns, 0.9),
            ("turning_point", self.turning_point_patterns, 0.9),
            ("revelation", self.revelation_patterns, 0.85),
            ("cliffhanger", self.cliffhanger_patterns, 0.85),
            ("setup", self.setup_patterns, 0.8),
            ("falling_action", self.falling_action_patterns, 0.7),
            ("resolution", self.resolution_patterns, 0.7),
            ("rising_action", self.rising_action_patterns, 0.6),
            ("opening", self.opening_patterns, 0.6),
        ]

    def _detect_role(self, text: str, frag: NarrativeFragment) -> str:
        """Detect scene role from text content and fragment metadata."""
        text_lower = text.lower() if text else ""

        # First, check tension (strongest signal)
        tension = getattr(frag, "tension", None) or 0.0
        if tension >= 0.7:
            return "climax"
        elif tension >= 0.4:
            return "rising_action"

        # Use emotion intensity
        emotion_intensity = getattr(frag, "emotion_intensity", None) or 0.0
        if emotion_intensity >= 0.7:
            return "climax"
        elif emotion_intensity >= 0.4:
            return "rising_action"

        # Check specific patterns in priority order
        for role_name, patterns, threshold in self._pattern_map:
            match_count = sum(1 for p in patterns if p.search(text_lower))
            if match_count >= 1:
                return role_name

        # Default: use position-based heuristics on the first line
        first_line = (text or "").split("\n")[0][:100].lower()
        if first_line:
            for p in self.opening_patterns:
                if p.search(first_line):
                    return "opening"

        return "rising_action"

    def assign_roles(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        """Assign scene roles to all fragments."""
        for frag in fragments:
            self.stats["fragments_processed"] += 1

            if frag.scene_role and frag.scene_role in SCENE_ROLES:
                # Check existing role seems reasonable
                self.stats["existing_kept"] += 1
                continue

            # Detect role
            role = self._detect_role(frag.text, frag)
            frag.scene_role = role
            self.stats["roles_assigned"] += 1
            self.stats["by_role"][role] += 1

            # Add retrieval tag
            if f"scene_role:{role}" not in frag.retrieval_tags:
                frag.retrieval_tags.append(f"scene_role:{role}")

        logger.info(
            f"Scene role assignment: {self.stats['fragments_processed']} fragments, "
            f"{self.stats['roles_assigned']} assigned, "
            f"{self.stats['existing_kept']} existing kept"
        )

        return fragments

    def assign_narrative_functions(
        self, fragments: List[NarrativeFragment]
    ) -> List[NarrativeFragment]:
        """Assign narrative functions to fragments missing them."""
        function_patterns = {
            "exposition": [
                r'\bexplain(?:ed|ing|s)?\b', r'\bdescribe(?:d|ing|s)?\b',
                r'\btold\s+about\b', r'\bhistory\b', r'\bbackground\b',
                r'\bcontext\b', r'\binformation\b', r'\bknown\s+as\b',
                r'\bwas\s+a\s+\w+\s+who\b', r'\bcalled\b', r'\bnamed\b',
            ],
            "conflict_escalation": [
                r'\bargu(?:e|ing|ment|ed)\b', r'\bconflict\b',
                r'\bfight(?:ing|s)?\b', r'\bdisagree(?:d|ing|s)?\b',
                r'\bquarrel(?:ed|ing|s)?\b', r'\btension\b.*\bgrew\b',
                r'\bhostile\b', r'\bconfront(?:ation|ed|ing)\b',
            ],
            "character_development": [
                r'\brealiz(?:ed|ation|ing)?\b', r'\bunderstand(?:ing|s)?\b',
                r'\bsuddenly\s+knew\b', r'\bgrew\b',
                r'\blearn(?:ed|ing|s)?\s+(?:from|about)\b',
                r'\bchanged?\b', r'\bevolve(?:d)?\b',
                r'\bthought\s+(?:about|of|back)\b',
                r'\breflect(?:ed|ing|s)?\b', r'\bremember(?:ed|ing|s)?\b',
            ],
            "worldbuilding": [
                r'\bcity\b', r'\btown\b', r'\bbuilding\b',
                r'\bstreet\b', r'\blandscape\b', r'\bkingdom\b',
                r'\bcountry\b', r'\bworld\b', r'\bland\b',
                r'\bdescribed?\s+(?:the|a|an)\s+(?:city|town|land|country)\b',
                r'\bculture?\b', r'\bpeople\s+of\b',
            ],
            "plot_advancement": [
                r'\bthen\b', r'\bnext\b', r'\bafter\b', r'\bfollowed\b',
                r'\bproceeded\b', r'\bcontinued\b', r'\bmoved\s+on\b',
                r'\bwent\b', r'\bcame\b', r'\bleft\b', r'\barrived\b',
            ],
            "tension_building": [
                r'\bsuddenly\b', r'\babruptly\b', r'\bwithout\s+warning\b',
                r'\bdanger\b', r'\bthreat(?:ened|ening)?\b',
                r'\bloom(?:ed|ing)?\b', r'\bdread\b', r'\bforeboding\b',
                r'\bofficial\b', r'\bimpending\b', r'\bapproaching\b',
            ],
            "revelation": [
                r'\breveal(?:ed|ing|s|ation)?\b', r'\bdiscover(?:ed|y|ing|s)?\b',
                r'\bfind\s+out\b', r'\btruth\b', r'\bsecret\b',
                r'\bexpose(?:d)?\b', r'\buncover(?:ed)?\b',
            ],
            "relief": [
                r'\brelieved?\b', r'\brelief\b', r'\bsafe\b',
                r'\bsaved?\b', r'\brescued?\b',
                r'\bpeace(?:ful)?\b', r'\bcalm(?:ed|ly)?\b',
                r'\bthank\s+(?:god|heavens|goodness)\b',
            ],
            "thematic": [
                r'\breflect(?:ed|ing|s)?\s+on\b', r'\bphilosophy\b',
                r'\bmeaning\s+of\b', r'\bnature\s+of\b',
                r'\btruth\s+(?:about|of)\b', r'\blife\s+and\b',
                r'\bdeath\s+and\b', r'\blove\s+and\b',
                r'\bwar\s+and\b', r'\bpeace\s+and\b',
            ],
        }

        for frag in fragments:
            if not frag.narrative_function:
                text_lower = (frag.text or "").lower()
                best_function = "plot_advancement"
                best_count = 0

                for func_name, patterns in function_patterns.items():
                    count = sum(
                        1 for p in patterns
                        if re.search(p, text_lower)
                    )
                    if count > best_count:
                        best_count = count
                        best_function = func_name

                frag.narrative_function = best_function
                if f"func:{best_function}" not in frag.retrieval_tags:
                    frag.retrieval_tags.append(f"func:{best_function}")

        return fragments

    def get_stats(self) -> Dict:
        """Get assignment statistics."""
        return dict(self.stats)
