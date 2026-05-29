from backend.core.data_models import Scene, SceneType
from backend.core.narrative_intelligence import ForeshadowingTracker
from backend.research.character_arc_tracker import ArcStage, CharacterArcTracker
from backend.research.coherence_scorer import CoherenceScorer
from backend.research.dialogue_intelligence import DialogueIntelligence, EmotionalTone, SpeakerIntent
from backend.research.embedding_encoder import EmbeddingEncoder
from backend.research.embedding_memory import MemoryEntry, MemoryImportanceScorer
from backend.research.memory_manager import MemoryManager
from backend.research.repetition_detector import RepetitionDetector
from backend.research.scene_purpose_validator import ScenePurpose, ScenePurposeValidator
from backend.research.vector_store import SemanticMemoryRetriever, VectorStore


def test_memory_manager_character_memory_context_and_symmetric_relationship():
    manager = MemoryManager()
    manager.register_character("Asha", "protagonist", ("careful",))
    manager.register_character("Ravi", "antagonist", ("ruthless",))
    manager.get_character_memory("Asha").track_goal("Find the archive", 1)
    manager.record_character_relationship("Asha", "Ravi", "enemy", 0.9, 1)

    context = manager.assemble_chapter_context(2, ["Asha", "Ravi"])

    assert context["character_states"]["Asha"]["active_goals"][0]["description"] == "Find the archive"
    assert manager.get_character_memory("Asha").get_relationship("Ravi").relationship_type == "enemy"
    assert manager.get_character_memory("Ravi").get_relationship("Asha").relationship_type == "enemy"


def test_arc_tracker_monotonic_and_stagnation_detection():
    tracker = CharacterArcTracker()
    tracker.track_progression("Asha", 1, ArcStage.discovering)
    tracker.track_progression("Asha", 2, ArcStage.unaware)
    assert tracker.current_stage("Asha") == ArcStage.discovering

    for chapter in (3, 4, 5):
        tracker.track_progression("Asha", chapter, ArcStage.discovering)
    assert tracker.detect_stagnation("Asha")


def test_scene_purpose_dialogue_and_resolution_detection():
    validator = ScenePurposeValidator()
    purposes = validator.detect_purposes(
        "A clue revealed the truth and the conflict was resolved.",
        {"scene_type": "dialogue"},
    )
    assert ScenePurpose.provide_information in purposes
    assert ScenePurpose.resolve_conflict in purposes


def test_dialogue_intelligence_generates_intent_and_tone():
    dialogue = DialogueIntelligence()
    line = dialogue.generate_dialogue_line(
        SpeakerIntent.question,
        EmotionalTone.fearful,
        {"speaker": "Asha", "listener": "Ravi", "subject": "the map"},
    )
    result = dialogue.analyze_dialogue(line, "Asha", "Ravi")
    assert result["intent"] == SpeakerIntent.question
    assert result["tone"] == EmotionalTone.fearful


def test_repetition_detector_reports_phrase_repetition():
    report = RepetitionDetector().analyze(
        ["The old archive opened slowly.", "The old archive opened again."],
        scene_types=["setup", "setup", "setup", "action"],
        beats=["clue", "clue", "clue", "payoff"],
    )
    assert report.phrase_repetition_rate > 0
    assert report.diversity_score < 1.0


def test_coherence_scorer_returns_dimension_scores():
    result = CoherenceScorer().score(
        ["Asha found the clue. Because Ravi had hidden it, she understood the threat."],
        registered_names={"Asha", "Ravi"},
    )
    assert set(result.scores) == {"character", "emotional", "causal", "continuity"}
    assert 0.0 <= result.overall <= 1.0


def test_foreshadowing_setup_payoff_quality_and_gap_validation():
    tracker = ForeshadowingTracker()
    tracker.register_setup("map", 1, "The torn map showed a hidden archive.")
    tracker.register_setup("map", 2, "A hidden archive mark appeared on the map.")
    tracker.register_payoff("map", 6, "The map revealed the hidden archive.")
    assert tracker.score_setup_payoff_quality("map") > 0
    assert tracker.validate_coverage() == []


def test_embedding_memory_encoder_vector_retrieval_round_trip(tmp_path):
    scene = Scene(1, SceneType.DIALOGUE, "Asha discovered a secret promise in Delhi.", 8, 0.5)
    entry = MemoryEntry.from_scene(scene, {"chapter_num": 1, "protagonist": "Asha", "memory_type": "secret"})
    assert entry.importance >= MemoryImportanceScorer().score(scene.content, {"memory_type": "secret"})

    encoder = EmbeddingEncoder()
    vector = encoder.encode(entry.text)
    assert len(vector) == 384

    store = VectorStore()
    retriever = SemanticMemoryRetriever(encoder, store)
    retriever.add_memory(entry)
    results = retriever.retrieve("secret promise Delhi", top_k=1, filters={"characters": ["Asha"]})
    assert results[0].scene_id == entry.scene_id

    path = tmp_path / "vectors.json"
    store.save(path)
    restored = VectorStore.load(path)
    assert len(restored) == 1
