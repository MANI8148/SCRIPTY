from backend.core.data_models import Chapter, Scene, SceneType
from backend.research.scene_dataset_generator import SceneDatasetGenerator, SceneFeatureExtractor


def test_feature_extraction_schema_and_normalization():
    extractor = SceneFeatureExtractor()
    features = extractor.extract(
        {
            "genre": "mystery",
            "previous_scene_type": "dialogue",
            "tension": 0.7,
            "protagonist_arc_stage": "confronting",
            "antagonist_arc_stage": "discovering",
            "unresolved_conflicts": ["secret", "map"],
        },
        scene_index=2,
        scene_count=5,
    )

    assert features["genre"] == "mystery"
    assert features["scene_position"] == 0.5
    assert features["previous_scene_type_id"] >= 0
    assert len(extractor.vectorize(features)) == 7


def test_examples_from_chapters_targets_next_scene_type():
    chapter = Chapter(
        chapter_num=1,
        title="Chapter 1",
        scenes=[
            Scene(1, SceneType.DESCRIPTION, "Asha entered the archive.", 4, 0.2),
            Scene(2, SceneType.DIALOGUE, "Asha asked about the map.", 5, 0.5),
            Scene(3, SceneType.ACTION, "Ravi attacked.", 2, 0.8),
        ],
        word_count=11,
        summary="Asha investigates.",
    )

    examples = SceneDatasetGenerator().examples_from_chapters([chapter], {"genre": "historical"})

    assert len(examples) == 2
    assert examples[0].target == "dialogue"
    assert examples[1].target == "action"


def test_generate_split_and_save_dataset(tmp_path):
    generator = SceneDatasetGenerator()
    examples = generator.generate_synthetic_dataset(book_count=10)
    splits = generator.split_dataset(examples)

    assert len(examples) >= 80
    assert set(splits) == {"train", "validation", "test"}
    assert sum(len(items) for items in splits.values()) == len(examples)

    json_path = generator.save_json(splits, tmp_path / "scene_dataset.json")
    csv_path = generator.save_csv(examples[:3], tmp_path / "scene_dataset.csv")
    assert json_path.exists()
    assert csv_path.exists()
