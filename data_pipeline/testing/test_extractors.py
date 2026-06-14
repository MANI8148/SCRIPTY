import pytest
from data_pipeline.extractors.dialogue_extractor import DialogueExtractor
from data_pipeline.extractors.body_language_extractor import BodyLanguageExtractor
from data_pipeline.extractors.action_extractor import ActionExtractor
from data_pipeline.extractors.reaction_extractor import ReactionExtractor
from data_pipeline.extractors.memory_extractor import MemoryExtractor
from data_pipeline.extractors.sensory_extractor import SensoryExtractor
from data_pipeline.extractors.thought_extractor import ThoughtExtractor
from data_pipeline.extractors.emotion_extractor import EmotionExtractor
from data_pipeline.extractors.relationship_extractor import RelationshipExtractor


class TestDialogueExtractor:
    def test_extract_dialogue(self):
        extractor = DialogueExtractor()
        text = '"I don\'t trust him," she said.'
        results = extractor.extract(text, 0)
        assert len(results) > 0
        assert results[0]["category"] == "dialogue"

    def test_extract_argument(self):
        extractor = DialogueExtractor()
        text = '"How dare you!" she shouted. "You never listen!"'
        results = extractor.extract(text, 0)
        assert len(results) >= 2

    def test_extract_speaker(self):
        extractor = DialogueExtractor()
        text = 'John said, "Hello there."'
        results = extractor.extract(text, 0)
        assert results[0]["speaker"] == "John"


class TestBodyLanguageExtractor:
    def test_extract_facial_expression(self):
        extractor = BodyLanguageExtractor()
        text = "She smiled warmly and raised an eyebrow."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_extract_movement(self):
        extractor = BodyLanguageExtractor()
        text = "He paced back and forth, then leaned forward."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_no_body_language(self):
        extractor = BodyLanguageExtractor()
        text = "The building was tall and made of stone."
        results = extractor.extract(text, 0)
        assert len(results) == 0


class TestActionExtractor:
    def test_extract_actions(self):
        extractor = ActionExtractor()
        text = "He ran across the field and jumped over the fence."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_extract_investigation(self):
        extractor = ActionExtractor()
        text = "She examined the evidence carefully and analyzed every detail."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestReactionExtractor:
    def test_emotional_reaction(self):
        extractor = ReactionExtractor()
        text = "She was shocked by the news and burst into tears."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_physical_reaction(self):
        extractor = ReactionExtractor()
        text = "His heart pounded as the blood ran cold."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestMemoryExtractor:
    def test_flashback(self):
        extractor = MemoryExtractor()
        text = "She remembered the day clearly, flashing back to that moment."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_regret(self):
        extractor = MemoryExtractor()
        text = "If only he hadn't made that mistake. He regretted it deeply."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestSensoryExtractor:
    def test_visual_sensory(self):
        extractor = SensoryExtractor()
        text = "She saw the golden light and watched the shadows dance."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_multiple_senses(self):
        extractor = SensoryExtractor()
        text = "She heard the music and smelled the flowers. The warm breeze touched her skin."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestThoughtExtractor:
    def test_beliefs(self):
        extractor = ThoughtExtractor()
        text = "He believed that justice would prevail in the end."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_goals(self):
        extractor = ThoughtExtractor()
        text = "She wanted to find the truth and needed to solve the mystery."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_fears(self):
        extractor = ThoughtExtractor()
        text = "He feared the darkness and was terrified of what lurked within."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestEmotionExtractor:
    def test_anger(self):
        extractor = EmotionExtractor()
        text = "He was furious and enraged by the betrayal."
        results = extractor.extract(text, 0)
        assert len(results) > 0
        assert results[0]["emotion"] == "anger"

    def test_fear(self):
        extractor = EmotionExtractor()
        text = "She was terrified and filled with dread."
        results = extractor.extract(text, 0)
        assert len(results) > 0
        assert results[0]["emotion"] == "fear"

    def test_joy(self):
        extractor = EmotionExtractor()
        text = "She was absolutely delighted and overjoyed by the news."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_tension_high(self):
        extractor = EmotionExtractor()
        text = "Suddenly, without warning, the door crashed open. Danger!"
        tension = extractor.estimate_tension(text)
        assert tension > 0.5

    def test_stakes_high(self):
        extractor = EmotionExtractor()
        text = "It was a life or death situation. Everything depended on this moment."
        stakes = extractor.estimate_stakes(text)
        assert stakes > 0.5

    def test_emotion_intensity(self):
        extractor = EmotionExtractor()
        text = "She was overwhelmed with joy and ecstatic happiness."
        results = extractor.extract(text, 0)
        assert len(results) > 0
        assert results[0]["emotion_intensity"] > 0.5


class TestRelationshipExtractor:
    def test_friendship(self):
        extractor = RelationshipExtractor()
        text = "John and Mary were close friends and trusted companions."
        results = extractor.extract(text, 0)
        assert len(results) > 0
        assert "friendships" in results[0]["subcategory"]

    def test_betrayal(self):
        extractor = RelationshipExtractor()
        text = "He felt the sting of betrayal as his closest ally turned against him."
        results = extractor.extract(text, 0)
        assert len(results) > 0

    def test_romance(self):
        extractor = RelationshipExtractor()
        text = "They were deeply in love, a passionate romance."
        results = extractor.extract(text, 0)
        assert len(results) > 0


class TestExtractorsEndToEnd:
    def test_all_extractors_paragraph(self):
        text = '"I don\'t trust him," she said, crossing her arms. Her heart pounded with fear. She remembered the last betrayal.'
        results = []
        results.extend(DialogueExtractor().extract(text, 0))
        results.extend(BodyLanguageExtractor().extract(text, 0))
        results.extend(EmotionExtractor().extract(text, 0))
        results.extend(MemoryExtractor().extract(text, 0))
        assert len(results) >= 3
