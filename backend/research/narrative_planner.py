from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from backend.core.data_models import SceneType


@dataclass
class SceneBeat:
    scene_num: int
    beat_type: str          # "setup", "rising", "climax", "falling", "resolution"
    target_tension: float   # [0.0, 1.0]
    required_scene_type: str  # SceneType value
    required_arc_stage: str = "unaware"
    required_purposes: list[str] = field(default_factory=list)
    foreshadowing_hints: list[str] = field(default_factory=list)


@dataclass
class ChapterPlan:
    chapter_num: int
    act: str                # "setup", "confrontation", "resolution"
    objective: str          # one-sentence chapter goal
    scene_beats: list[SceneBeat]
    target_tension: float


@dataclass
class ActPlan:
    act_name: str
    chapter_range: tuple[int, int]  # inclusive
    act_goal: str


@dataclass
class BookPlan:
    session_id: str
    genre: str
    protagonist_goal: str
    antagonist_goal: str
    setting: dict
    chapter_count: int
    act_plans: list[ActPlan]
    chapter_plans: list[ChapterPlan]
    arc_template: str       # e.g. "three_act", "hero_journey", "rising_action"

    @property
    def chapters(self) -> list[ChapterPlan]:
        """Backward-compatible alias for older planner callers."""
        return self.chapter_plans


# ---------------------------------------------------------------------------
# Arc template control points: list of (position [0,1], tension [0,1]) pairs
# ---------------------------------------------------------------------------
_ARC_TEMPLATES: dict[str, list[tuple[float, float]]] = {
    "three_act": [
        (0.00, 0.20),
        (0.25, 0.50),
        (0.75, 0.90),
        (0.85, 0.70),
        (1.00, 0.40),
    ],
    "hero_journey": [
        (0.00, 0.30),
        (0.20, 0.60),
        (0.45, 0.80),
        (0.60, 0.50),
        (0.80, 0.90),
        (1.00, 0.30),
    ],
    "rising_action": [
        (0.00, 0.20),
        (0.80, 0.90),
        (1.00, 0.30),
    ],
}


def _interpolate_tension(position: float, control_points: list[tuple[float, float]]) -> float:
    """Linear interpolation over arc template control points."""
    if position <= control_points[0][0]:
        return control_points[0][1]
    if position >= control_points[-1][0]:
        return control_points[-1][1]
    for i in range(len(control_points) - 1):
        x0, y0 = control_points[i]
        x1, y1 = control_points[i + 1]
        if x0 <= position <= x1:
            t = (position - x0) / (x1 - x0)
            return round(y0 + t * (y1 - y0), 4)
    return control_points[-1][1]


def _beat_type_for_tension(tension: float) -> str:
    if tension < 0.30:
        return "setup"
    if tension < 0.50:
        return "rising"
    if tension < 0.75:
        return "rising"
    if tension < 0.85:
        return "climax"
    if tension < 0.95:
        return "falling"
    return "resolution"


def _scene_type_for_tension(tension: float) -> str:
    if tension > 0.65:
        return SceneType.ACTION.value
    if tension > 0.45:
        return SceneType.DIALOGUE.value
    return SceneType.DESCRIPTION.value


def _arc_stage_for_act(act_name: str, chapter_num: int, chapter_count: int) -> str:
    if act_name == "setup":
        return "discovering" if chapter_num > 1 else "unaware"
    if act_name == "confrontation":
        return "confronting"
    return "resolving"


def _purposes_for_act(act_name: str) -> list[str]:
    if act_name == "confrontation":
        return ["advance_plot", "increase_tension"]
    if act_name == "resolution":
        return ["resolve_conflict", "reveal_character"]
    return ["provide_information", "reveal_character"]


class NarrativePlanner:
    def __init__(
        self,
        genre: str = "general",
        arc_template: str = "three_act",
        act_ratios: tuple[float, float, float] = (0.25, 0.50, 0.25),
    ) -> None:
        self.genre = genre
        self.arc_template = arc_template
        self.act_ratios = act_ratios
        self._plan: Optional[BookPlan] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_plan(self, goal_spec: dict | int) -> BookPlan:
        """Create a BookPlan from a goal_spec dict.

        Required keys: chapter_count
        Optional keys: genre, protagonist_goal, antagonist_goal, setting,
                       arc_template, session_id
        """
        if isinstance(goal_spec, int):
            goal_spec = {"chapter_count": goal_spec, "genre": self.genre}
        chapter_count: int = goal_spec.get("chapter_count", 10)
        genre: str = goal_spec.get("genre", self.genre)
        protagonist_goal: str = goal_spec.get("protagonist_goal", "")
        antagonist_goal: str = goal_spec.get("antagonist_goal", "")
        setting: dict = goal_spec.get("setting", {})
        arc_template: str = goal_spec.get("arc_template", self.arc_template)
        session_id: str = goal_spec.get("session_id", "")

        control_points = _ARC_TEMPLATES.get(arc_template, _ARC_TEMPLATES["three_act"])

        # Build act plans
        first_end = max(1, round(chapter_count * self.act_ratios[0]))
        second_end = max(first_end + 1, round(chapter_count * (self.act_ratios[0] + self.act_ratios[1])))
        act_plans = [
            ActPlan(
                act_name="setup",
                chapter_range=(1, first_end),
                act_goal="Establish characters, setting, and central conflict.",
            ),
            ActPlan(
                act_name="confrontation",
                chapter_range=(first_end + 1, second_end),
                act_goal="Escalate conflict and raise stakes.",
            ),
            ActPlan(
                act_name="resolution",
                chapter_range=(second_end + 1, chapter_count),
                act_goal="Resolve conflict and conclude character arcs.",
            ),
        ]

        # Build chapter plans
        chapter_plans: list[ChapterPlan] = []
        for chapter_num in range(1, chapter_count + 1):
            position = (chapter_num - 1) / max(chapter_count - 1, 1)
            tension = _interpolate_tension(position, control_points)

            act_name = "resolution"
            for ap in act_plans:
                if ap.chapter_range[0] <= chapter_num <= ap.chapter_range[1]:
                    act_name = ap.act_name
                    break

            beat_type = _beat_type_for_tension(tension)
            scene_type = _scene_type_for_tension(tension)

            scene_beat = SceneBeat(
                scene_num=1,
                beat_type=beat_type,
                target_tension=tension,
                required_scene_type=scene_type,
                required_arc_stage=_arc_stage_for_act(act_name, chapter_num, chapter_count),
                required_purposes=_purposes_for_act(act_name),
                foreshadowing_hints=(
                    [f"Hint toward final payoff in chapter {chapter_count}"]
                    if chapter_num <= max(1, chapter_count - 3) and chapter_num in {1, 2, max(3, chapter_count // 2)}
                    else []
                ),
            )

            chapter_plans.append(ChapterPlan(
                chapter_num=chapter_num,
                act=act_name,
                objective=f"{act_name.capitalize()} — chapter {chapter_num} of {chapter_count}.",
                scene_beats=[scene_beat],
                target_tension=tension,
            ))

        self._plan = BookPlan(
            session_id=session_id,
            genre=genre,
            protagonist_goal=protagonist_goal,
            antagonist_goal=antagonist_goal,
            setting=setting,
            chapter_count=chapter_count,
            act_plans=act_plans,
            chapter_plans=chapter_plans,
            arc_template=arc_template,
        )
        return self._plan

    def get_chapter_plan(self, chapter_num: int) -> ChapterPlan:
        if self._plan is None:
            raise ValueError("create_plan must be called first")
        return self._plan.chapter_plans[chapter_num - 1]

    def get_target_tension(self, chapter_num: int) -> float:
        if self._plan is None:
            raise ValueError("create_plan must be called first")
        return self._plan.chapter_plans[chapter_num - 1].target_tension

    def serialize(self, session_id: str, output_dir: str) -> Path:
        """Serialize BookPlan to {output_dir}/{session_id}/plan.json.

        Older callers used serialize(output_dir, session_id), so if the first
        argument looks like an existing directory and the second does not, swap
        them.
        """
        if self._plan is None:
            raise ValueError("no plan to serialize")
        if Path(session_id).exists() and not Path(output_dir).exists():
            session_id, output_dir = output_dir, session_id
        target = Path(output_dir) / session_id / "plan.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        def _convert(obj):
            if isinstance(obj, SceneBeat):
                return {
                    "scene_num": obj.scene_num,
                    "beat_type": obj.beat_type,
                    "target_tension": obj.target_tension,
                    "required_scene_type": obj.required_scene_type,
                    "required_arc_stage": obj.required_arc_stage,
                    "required_purposes": list(obj.required_purposes),
                    "foreshadowing_hints": list(obj.foreshadowing_hints),
                }
            if isinstance(obj, ChapterPlan):
                return {
                    "chapter_num": obj.chapter_num,
                    "act": obj.act,
                    "objective": obj.objective,
                    "scene_beats": [_convert(b) for b in obj.scene_beats],
                    "target_tension": obj.target_tension,
                }
            if isinstance(obj, ActPlan):
                return {
                    "act_name": obj.act_name,
                    "chapter_range": list(obj.chapter_range),
                    "act_goal": obj.act_goal,
                }
            if isinstance(obj, BookPlan):
                return {
                    "session_id": obj.session_id,
                    "genre": obj.genre,
                    "protagonist_goal": obj.protagonist_goal,
                    "antagonist_goal": obj.antagonist_goal,
                    "setting": obj.setting,
                    "chapter_count": obj.chapter_count,
                    "act_plans": [_convert(a) for a in obj.act_plans],
                    "chapter_plans": [_convert(c) for c in obj.chapter_plans],
                    "arc_template": obj.arc_template,
                }
            return obj

        target.write_text(
            json.dumps(_convert(self._plan), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target
