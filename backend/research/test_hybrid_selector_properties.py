from backend.research.hybrid_scene_selector import HybridSceneSelector, SceneConstraint


def test_hybrid_selector_blocks_three_consecutive_action_scenes():
    selector = HybridSceneSelector()
    selected = selector.select_next_scene(
        {"action": 0.95, "dialogue": 0.02, "description": 0.01, "introspection": 0.01, "transition": 0.01},
        [SceneConstraint("max_consecutive", {"scene_type": "action", "limit": 2})],
        previous_scene_types=["action", "action"],
    )

    assert selected != "action"
    assert selector.decision_stats["rule_override"] == 1


def test_hybrid_selector_blocks_impossible_transition():
    selector = HybridSceneSelector()
    selected = selector.select_next_scene(
        {"setup": 1.0, "description": 0.1},
        [],
        previous_scene_types=["dialogue"],
        current_beat="resolution",
    )

    assert selected != "setup"


def test_ml_predictions_influence_at_least_sixty_percent_without_violations():
    selector = HybridSceneSelector()
    constraints = selector.default_constraints()
    previous: list[str] = []
    for _ in range(10):
        selected = selector.select_next_scene(
            {"dialogue": 0.75, "action": 0.1, "description": 0.05, "introspection": 0.05, "transition": 0.05},
            constraints,
            previous_scene_types=previous,
        )
        previous.append(selected)
        if len(previous) > 2:
            previous = previous[-2:]

    assert selector.ml_influence_rate() >= 0.6


def test_require_one_of_constraint_is_never_violated():
    selector = HybridSceneSelector()
    selected = selector.select_next_scene(
        {"action": 0.9, "dialogue": 0.1},
        [SceneConstraint("require_one_of", {"scene_types": ["dialogue"]})],
    )

    assert selected == "dialogue"
