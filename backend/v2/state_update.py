from __future__ import annotations

import uuid

from backend.v2.character_agent import CharacterAgent
from backend.v2.memory_system import MemorySystem
from backend.v2.types import (
    AgentState,
    CharacterBeliefs,
    GeneratedScene,
    MemoryEntry,
    RelationKind,
    WorldConstraints,
)


# Perception/action verbs that signal a belief-forming moment in scene text.
_BELIEF_VERBS = (
    "discovered", "realized", "saw", "found", "learned", "understood",
    "recognized", "noticed", "remembered", "decided", "knew", "observed",
    "felt", "heard", "believed", "suspected", "watched", "witnessed",
    "uncovered", "grasped",
)


class StateUpdater:
    """Updates character beliefs, memory, and emotional state after each scene.

    No metadata-only flows — every update directly affects future generation.
    """

    def update_characters(
        self,
        agents: list[CharacterAgent],
        scene: GeneratedScene,
        world: WorldConstraints,
        memory: MemorySystem | None = None,
        chapter_num: int = 0,
    ) -> None:
        for agent in agents:
            self._update_beliefs(agent, scene)
            self._update_emotional_pressure(agent, scene, world)
            self._update_arc_phase(agent, scene)

        # Sentiment modulation only — relationship delta detection is in record_relationship_deltas()
        if memory is not None:
            chars = scene.characters_involved
            for i, a_name in enumerate(chars):
                agent_a = next((a for a in agents if a.name == a_name), None)
                if agent_a is None:
                    continue
                for b_name in chars[i + 1:]:
                    agent_b = next((a for a in agents if a.name == b_name), None)
                    if agent_b is None:
                        continue

                    # Modulate emotional pressure using relationship sentiment
                    sentiment = memory.current_relationship_sentiment(a_name, b_name)
                    if sentiment < 0:
                        agent_a.emotional_pressure = min(1.0, agent_a.emotional_pressure + abs(sentiment) * 0.1)
                        agent_b.emotional_pressure = min(1.0, agent_b.emotional_pressure + abs(sentiment) * 0.1)

    def record_scene_memory(
        self,
        memory: MemorySystem,
        scene: GeneratedScene,
        chapter_num: int,
        scene_num: int,
        agents: list[CharacterAgent] | None = None,
    ) -> None:
        # Phase 6: Semantic memory — record facts from scene content
        scene_text = scene.content
        scene_lower = scene_text.lower()

        # Extract potential facts: sentences containing character names + discovery/realization verbs
        if agents:
            for agent in agents:
                if agent.name in scene.characters_involved:
                    for sentence in scene_text.split("."):
                        if agent.name in sentence and any(w in sentence.lower()
                            for w in ["discover", "realize", "know", "learn", "see", "find", "understand",
                                      "recognize", "notice", "aware", "remember"]):
                            fact_text = sentence.strip().strip(",").strip(".").strip()
                            if fact_text and len(fact_text) > 10:
                                memory.record_fact(
                                    text=fact_text[:200],
                                    chapter_num=chapter_num,
                                    scene_num=scene_num,
                                    characters=[agent.name],
                                )

        # Seed semantic facts into agent beliefs for prose injection
        if agents:
            for agent in agents:
                if agent.name in scene.characters_involved:
                    all_facts = list(memory.semantic.facts.values())
                    for fact_entry in all_facts[-5:]:
                        if fact_entry.characters and fact_entry.characters[0] == agent.name:
                            agent.beliefs.discovered.append(
                                f"understood that {fact_entry.text[:80]}"
                            )

        # Episodic memory
        memory.record_event(
            text=scene_text[:200],
            chapter_num=chapter_num,
            scene_num=scene_num,
            characters=scene.characters_involved,
            relevance_score=scene.tension,
        )
        for char in scene.characters_involved:
            memory.beliefs_for(char).discovered.append(scene_text[:100])

        # Interpretation and Consequence memory are recorded by the dedicated
        # record_interpretations() and record_consequences() methods called
        # from engine.py to avoid double-recording. Only keep unique recording.
        # Phase 5: Callback scheduling — scenes with meaningful tension schedule future callbacks
        if scene.tension > 0.4:
            callback_id = str(uuid.uuid4())
            callback_data = {
                "_callback_id": callback_id,
                "resurface_text": f"A tense moment from chapter {chapter_num} still haunted {', '.join(scene.characters_involved)}.",
                "characters": scene.characters_involved,
            }
            memory.schedule_callback(
                memory_id=f"scene_{chapter_num}_{scene_num}_{callback_id[:8]}",
                trigger_chapter=chapter_num + 1,
                callback_data=callback_data,
            )

        # Check for pending callbacks (Change 3)
        pending = memory.check_callbacks(chapter_num)
        for cb in pending:
            cb_id = cb.callback_data.get("_callback_id", "")
            if cb_id:
                for char in scene.characters_involved:
                    resurface_text = cb.callback_data.get(
                        "resurface_text",
                        f"A memory from the past resurfaced in chapter {cb.trigger_chapter}."
                    )
                    memory.beliefs_for(char).discovered.append(resurface_text)
                memory.mark_callback_fired(cb_id)

    def update_perceptions(
        self,
        agents: list[CharacterAgent],
        memory: MemorySystem,
        scene: GeneratedScene,
        chapter_num: int,
        scene_num: int,
    ) -> None:
        """Feed scene events to character perception systems so drift accumulates.

        This is the activation point for perceive() — without this call, drift
        history never accumulates across chapters and BehavioralDriftTracker
        always returns 'consistent' patterns.
        """
        for agent in agents:
            if agent.name in scene.characters_involved:
                event = MemoryEntry(
                    text=scene.content[:200],
                    source="generated",
                    chapter_num=chapter_num,
                    scene_num=scene_num,
                    characters=list(scene.characters_involved),
                    relevance_score=scene.tension,
                )
                agent.perceive(event)

    def record_interpretations(
        self,
        memory: MemorySystem,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
        chapter_num: int,
        scene_num: int,
    ) -> None:
        """Each character interprets key events through their own lens.

        Idempotent — safe to call multiple times per scene.
        """
        for agent in agents:
            if agent.name in scene.characters_involved:
                memory.interpret_event(
                    event_text=scene.content[:200],
                    character_name=agent.name,
                    character_traits=agent.character.traits,
                    chapter_num=chapter_num,
                    scene_num=scene_num,
                )

    def record_consequences(
        self,
        memory: MemorySystem,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
        chapter_num: int,
        scene_num: int,
    ) -> None:
        """Record consequences of major character actions.

        Uses each agent's last intention to build a consequence entry.
        Idempotent — safe to call multiple times per scene.
        """
        for agent in agents:
            if agent.name in scene.characters_involved:
                intention = getattr(agent, '_last_intention', None)
                if intention is not None:
                    memory.record_consequence(
                        character=agent.name,
                        action=intention.action if hasattr(intention, 'action') else 'interact',
                        consequence=f"{agent.name} attempted {intention.action if hasattr(intention, 'action') else 'to act'}",
                        success=scene.tension < 0.7,
                        impact=scene.tension,
                        chapter_num=chapter_num,
                        scene_num=scene_num,
                    )

    def record_relationship_deltas(
        self,
        memory: MemorySystem,
        scene: GeneratedScene,
        agents: list[CharacterAgent],
        chapter_num: int,
    ) -> None:
        """Detect and record relationship shifts based on scene interactions.

        Uses tension thresholds to detect when relationships should shift.
        Idempotent — safe to call multiple times per scene.
        """
        involved = [a for a in agents if a.name in scene.characters_involved]
        for i, agent_a in enumerate(involved):
            for agent_b in involved[i + 1:]:
                old_rel = agent_a.character.relationships.get(
                    agent_b.name, RelationKind.NEUTRAL
                )
                if scene.tension > 0.8:
                    if scene.tension > 0.85:
                        new_rel = RelationKind.ENEMY
                    else:
                        new_rel = RelationKind.RIVAL
                    trigger = f"high-tension interaction ({scene.tension:.2f})"
                elif scene.tension < 0.2 and old_rel in (RelationKind.ENEMY, RelationKind.RIVAL):
                    new_rel = RelationKind.NEUTRAL
                    trigger = f"low-tension resolution ({scene.tension:.2f})"
                else:
                    continue

                if old_rel != new_rel:
                    agent_a.character.relationships[agent_b.name] = new_rel
                    agent_b.character.relationships[agent_a.name] = new_rel
                    # Also update relationship_beliefs so the realizer can
                    # read them when composing character actions (A4 fix).
                    agent_a.beliefs.relationship_beliefs[agent_b.name] = new_rel.value
                    agent_b.beliefs.relationship_beliefs[agent_a.name] = new_rel.value
                    memory.record_relationship_delta(
                        a=agent_a.name, b=agent_b.name,
                        old_rel=old_rel, new_rel=new_rel,
                        trigger=trigger, chapter_num=chapter_num,
                    )

    def _update_beliefs(self, agent: CharacterAgent, scene: GeneratedScene) -> None:
        """Extract belief entries from scene content.

        Scans the scene text for sentences that mention the agent's name
        together with a perception/action verb (discovered, realized, saw,
        found, learned, ...). Each such sentence becomes a belief recorded in
        ``agent.beliefs.discovered``. When another involved character is also
        named in the same sentence, a relationship belief is captured so the
        realizer can read interpersonal state when composing later scenes.
        """
        if agent.name not in scene.characters_involved:
            return

        text = scene.content or ""
        seen: set[str] = set(agent.beliefs.discovered)

        for sentence in text.split("."):
            s = sentence.strip().strip(",").strip().strip(".").strip()
            if not s or agent.name not in s:
                continue
            if not any(verb in s.lower() for verb in _BELIEF_VERBS):
                continue

            belief = s[:160]
            if belief and belief not in seen:
                agent.beliefs.discovered.append(belief)
                seen.add(belief)

            # Co-mentioned character -> relationship belief
            for other in scene.characters_involved:
                if other != agent.name and other in s:
                    agent.beliefs.relationship_beliefs[other] = (
                        f"observed {other}: {s[:80]}"
                    )

    def _update_emotional_pressure(
        self,
        agent: CharacterAgent,
        scene: GeneratedScene,
        world: WorldConstraints,
    ) -> None:
        if agent.name in scene.characters_involved:
            agent.emotional_pressure = min(
                1.0,
                max(0.0, agent.emotional_pressure + scene.tension * 0.3),
            )
        else:
            agent.emotional_pressure = max(
                0.0,
                agent.emotional_pressure - 0.1,
            )

    def _update_arc_phase(
        self, agent: CharacterAgent, scene: GeneratedScene
    ) -> None:
        if agent.emotional_pressure > 0.8:
            agent.character.arc_phase = "peak"
        elif agent.emotional_pressure < 0.2:
            agent.character.arc_phase = "resolution"
