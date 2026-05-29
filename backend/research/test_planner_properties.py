from backend.research.narrative_planner import NarrativePlanner


def test_planner_tension_range_and_serialization(tmp_path):
    planner = NarrativePlanner(genre="historical")
    plan = planner.create_plan(10)
    assert len(plan.chapters) == 10
    assert all(0.0 <= chapter.target_tension <= 1.0 for chapter in plan.chapters)
    path = planner.serialize(str(tmp_path), "session")
    assert path.exists()

