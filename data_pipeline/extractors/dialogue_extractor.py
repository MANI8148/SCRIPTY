from typing import List, Optional
import re
from data_pipeline.schema.taxonomy import Category


DIALOGUE_PATTERNS = [
    re.compile(r'["\u201C]([^"\u201D]+)["\u201D]'),
    re.compile(r'["\u2018]([^"\u2019]+)["\u2019]'),
    re.compile(r"'([^']+)'"),
]

SUBTEXT_INDICATORS = {
    "subtext": ["what he didn't say", "what she really meant", "the unspoken", "silence said", "paused", "hesitated", "looked away"],
    "confession": ["confess", "admit", "truth is", "i have to tell", "i need to say", "the truth"],
    "argument": ["shout", "yell", "how dare", "you never", "you always", "argue", "disagree", "accuse"],
    "threat": ["or else", "if you don't", "you'll regret", "i'll make", "threaten", "warning"],
    "flirtation": ["tease", "flirt", "charm", "bat her eyes", "grin", "wink", "playful"],
    "negotiation": ["bargain", "deal", "offer", "trade", "propose", "condition", "compromise"],
}

SUB_CATEGORY_MAP = {
    "subtext": Category.DIALOGUE_SUBTEXT,
    "confession": Category.DIALOGUE_CONFESSIONS,
    "argument": Category.DIALOGUE_ARGUMENTS,
    "threat": Category.DIALOGUE_THREATS,
    "flirtation": Category.DIALOGUE_FLIRTATION,
    "negotiation": Category.DIALOGUE_NEGOTIATION,
}


class DialogueExtractor:
    def extract(self, text: str, paragraph_idx: int) -> List[dict]:
        results = []
        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                dialogue_text = match.group(1).strip()
                if len(dialogue_text) < 5:
                    continue

                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]

                subcategory = self._classify_dialogue(context, dialogue_text)

                speaker = self._extract_speaker(text, match.start())
                target = self._extract_target(context, speaker)

                item = {
                    "text": dialogue_text,
                    "full_text": text,
                    "paragraph": paragraph_idx,
                    "category": Category.DIALOGUE.value,
                    "subcategory": subcategory,
                    "speaker": speaker,
                    "target": target,
                    "confidence": 1.0 if subcategory == "dialogue" else 0.85,
                }
                results.append(item)
        return results

    def _classify_dialogue(self, context: str, dialogue_text: str) -> str:
        context_lower = context.lower()
        dialogue_lower = dialogue_text.lower()

        for sub_type, indicators in SUBTEXT_INDICATORS.items():
            for indicator in indicators:
                if indicator in context_lower or indicator in dialogue_lower:
                    return SUB_CATEGORY_MAP[sub_type].value
        return Category.DIALOGUE.value

    def _extract_speaker(self, text: str, dialogue_start: int) -> str:
        before = text[max(0, dialogue_start - 200):dialogue_start]
        patterns = [
            r'(?i)(\w+)\s+said',
            r'(?i)(\w+)\s+whispered',
            r'(?i)(\w+)\s+shouted',
            r'(?i)(\w+)\s+asked',
            r'(?i)(\w+)\s+replied',
            r'(?i)(\w+)\s+answered',
            r'(?i)(\w+)\s+murmured',
            r'(?i)(\w+)\s+yelled',
            r'(?i)(\w+)\s+cried',
            r'(?i)(\w+)\s+exclaimed',
        ]
        for pat in patterns:
            m = re.search(pat, before)
            if m:
                return m.group(1)
        return ""

    def _extract_target(self, context: str, speaker: str) -> str:
        patterns = [
            r'(?i)(?:to|at)\s+(\w+)',
            r'(?i)(?:at|toward)\s+(?:the\s+)?(\w+)',
        ]
        for pat in patterns:
            m = re.search(pat, context)
            if m and m.group(1).lower() != speaker.lower():
                return m.group(1)
        return ""
