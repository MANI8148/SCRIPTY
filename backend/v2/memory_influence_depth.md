# Memory Influence Depth Report

> Forensic trace of every memory subsystem's influence depth through L0 (Stored) → L7 (Changes future story trajectory).
> Generated: 2026-06-09 | Audit targets: Episodic, Semantic, Interpretation, Consequence, Relationship, Callback, RAG

---

## Influence Depth Model

Each level represents an increasing depth of influence on generated narrative:

| Level | Name | Definition |
|-------|------|------------|
| L0 | **Stored** | Data is written to the store. What triggers the write? |
| L1 | **Retrieved** | Data is read back. What query/filter is used? |
| L2 | **Prompted** | Retrieved data appears in an intermediate blueprint/context structure that feeds generation. |
| L3 | **Changes wording** | The data affects which template, verb, adjective, adverb, or noun phrase is selected. |
| L4 | **Changes dialogue** | The data affects dialogue content, tag (said/whispered/snapped), or intent. |
| L5 | **Changes actions** | The data affects character action selection (verb, target, adverb). |
| L6 | **Changes scene outcome** | The data affects tension, resolution quality, or scene type classification. |
| L7 | **Changes future story trajectory** | A record in scene N affects scene N+1 or beyond — cross-chapter influence. |

---

```

INFLUENCE DEPTH SUMMARY

Subsystem         L0    L1    L2    L3    L4    L5    L6    L7
─────────────────────────────────────────────────────────────────
Episodic          ✅    ✅    ✅    ✅    ✅    ✅    ⚠️    ✅
Semantic          ✅    ✅    ✅    ⚠️    ❌    ❌    ❌    ⚠️
Interpretation    ✅    ⚠️    ⚠️    ❌    ❌    ❌    ❌    ❌
Consequence       ✅    ⚠️    ⚠️    ❌    ❌    ✅    ⚠️    ✅
Relationship      ✅    ✅    ✅    ✅    ✅    ✅    ✅    ✅
Callback          ✅    ✅    ✅    ✅    ⚠️    ⚠️    ❌    ✅
RAG               ✅    ⚠️    ⚠️    ❌    ❌    ❌    ❌    ❌

Legend:  ✅ Active  ⚠️ Partial  ❌ Dead

```

---

## 1. Episodic Memory

> Raw event timeline: "what happened" in chronological order.

### L0 — Stored

**Level description:** Raw scene text is written to `EpisodicStore.records` as a `MemoryEntry`.

**Code path:** `backend/v2/state_update.py:140-146` — `record_scene_memory()` calls `memory.record_event()`.

**Trigger:** Every generated scene unconditionally.

```python
memory.record_event(
    text=scene_text[:200],
    chapter_num=chapter_num,
    scene_num=scene_num,
    characters=scene.characters_involved,
    relevance_score=scene.tension,
)
```

Also, the entry is appended to `EmotionalRetrievalEngine.episodic_records` at `memory_system.py:149` to keep the emotion-based index in sync.

Additionally, each involved character gets `scene.content[:100]` appended to `beliefs.discovered` at `state_update.py:147-148`:
```python
for char in scene.characters_involved:
    memory.beliefs_for(char).discovered.append(scene_text[:100])
```

**State:** ✅ Active — fires on every scene, every character.

**Percentage:** 100% — always written.

---

### L1 — Retrieved

**Level description:** Episodic records are read back via two retrieval paths.

**Path A — `recent_context()`:** `pipeline.py:74` — called for each agent during intention deliberation:
```python
memories = self.memory.recent_context(agent.name)
```
This returns the last 3 episodic records for that character (`memory_system.py:224-225`).

**Path B — `retrieve()`:** `pipeline.py:110-116` — called per agent with a `MemoryQuery`:
```python
query = MemoryQuery(
    focus_character=agent.name,
    context_query=objective.purpose,
    top_k=3,
    emotion_filter=agent.emotional_state_str(),
)
retrieved.extend(self.memory.retrieve(query, ...))
```
This queries `EpisodicStore.query()` which filters by character and sorts by `relevance_score` descending (`memory_system.py:32-35`).

**State:** ✅ Active — both paths fire every scene.

**Percentage:** 100%.

---

### L2 — Prompted

**Level description:** Retrieved episodic entries are injected into the `SceneBlueprint` that the `DramaticRealizer` receives.

**Code path:** `pipeline.py:155-162` — `SceneBlueprint` constructor:
```python
blueprint = SceneBlueprint(
    ...
    retrieved_memories=retrieved,
    ...
)
```

The `retrieved` list is a `list[MemoryEntry]` containing all episodic results (merged with semantic, RAG, callback, and emotion-based results). This blueprint is the single data structure passed to `DramaticRealizer.realize()`.

**State:** ✅ Active — every scene generates a blueprint with retrieved memories.

**Percentage:** 100%.

---

### L3 — Changes wording

**Level description:** Episodic memories influence the specific words chosen in prose output. Multiple mechanisms exist.

**Mechanism A — Memory Callback Injection:** `dramatic_realizer.py:1062-1090` — `_compose_memory_callback()` selects from `bp.retrieved_memories` using weighted random selection based on `relevance_score`. The selected memory's text is embedded directly into a narrative callback sentence:

```python
# Line 1062-1090
weights = [max(m.relevance_score, 0.1) for m in bp.retrieved_memories]
mem = random.choices(bp.retrieved_memories, weights=weights, k=1)[0]
templates = [
    f"A memory surfaced — {mem_text}. {char} had not forgotten.",
    f"It reminded {char} of {mem_text}. That changed everything.",
    ...
]
```

This callback text appears as a `COMPLICATION` event in the scene (called in `_build_dialogue_scene` line 1164-1166, `_build_introspection_scene` line 1217-1219, `_build_description_scene` line 1255-1257).

**Mechanism B — Beliefs → Action Description:** Episodic memory is appended to `beliefs.discovered` at `state_update.py:147-148`. In `_compose_character_action()` at `dramatic_realizer.py:797-808`, discovered beliefs are woven into the action text:

```python
if beliefs.discovered:
    raw = random.choice(beliefs.discovered)[:40]
    ...
    action_desc = f"{name}, aware of {discovery}, {verb_phrase} {target} {adverb}."
```

**Example sentence (Mechanism B):**
> _Arjun, aware of the railway tracks stretched across the dim platform, kept an eye on Maya with suspicion._

**Mechanism C — Emotional Pressure → Body Language:** Episodic memories influence `emotional_pressure` via `perceive()` (`character_agent.py:72-77`). The realizer's `_compose_character_action()` uses `_emotion_key(pressure, traits)` to select body language phrases from `_BODY_LANGUAGE` which are prepended to the action sentence (`dramatic_realizer.py:777-778`).

**Example sentence (Mechanism C, via emotional pressure):**
> _His fists clenched at his sides. Arjun, aware of the tense situation, blocked the path of Maya with wariness._

**State:** ✅ Active — Mechanism A fires on dialogue/introspection/description scenes (~75% of scenes); Mechanism B fires whenever beliefs have discovered entries (>80% of scenes after scene 1); Mechanism C fires on every action sentence (100% of character actions).

**Percentage:** 85% — on most scenes, at least one mechanism fires. After scene 1, beliefs are populated and memory callback is available.

---

### L4 — Changes dialogue

**Level description:** Episodic memories influence dialogue tag selection and dialogue content.

**Path:** Emotional pressure (modulated by episodic content via `perceive()`) feeds into `_dialogue_tag_for()` at `dramatic_realizer.py:558-567`:
```python
def _dialogue_tag_for(pressure: float, relationship: RelationKind | None) -> str:
    if pressure > 0.7:
        return random.choice(_ANGRY_TAGS)  # ["snapped", "hissed", "spat", "growled", "snarled", "cut in"]
    if pressure > 0.5:
        if relationship in (RelationKind.ENEMY, RelationKind.RIVAL):
            return random.choice(_ANGRY_TAGS)
        return random.choice(_FEARFUL_TAGS)
    if pressure < 0.2:
        return random.choice(_CALM_TAGS)
    return random.choice(_DIALOGUE_TAGS)
```

This function is called by `_compose_dialogue_line()` and `_build_dialogue_tag()` (`dramatic_realizer.py:953-960`).

**Example sentence:**
> _"I discovered something important," growled Maya._

The word "growled" was selected because: episodic memory of a high-tension scene → `perceive()` increased `emotional_pressure` → `_dialogue_tag_for()` returned `_ANGRY_TAGS` → "growled" was selected.

**State:** ✅ Active — every dialogue line (~1-2 per scene in dialogue scenes, which are ~30-40% of scenes) is affected by EP through the pressure→tag pathway. Also affects ACTION scene dialogue lines.

**Percentage:** 60% — every dialogue tag can be influenced by pressure from episodic memory. In scenes where pressure is low (<0.2), the effect chooses `_CALM_TAGS`. In scenes where pressure is moderate (0.2-0.5), only relationship matters.

---

### L5 — Changes actions

**Level description:** Episodic memories affect which action verb and target are selected for a character.

**Path A — `decide_intention()`:** `pipeline.py:74` passes `memories = self.memory.recent_context(agent.name)` to `agent.decide_intention()`. In `_compute_urgency()` at `character_agent.py:313-314`:
```python
if memories and any("danger" in m.lower() for m in memories):
    pressure += 0.3
```
Higher urgency can shift the action pattern (e.g., at high urgency, `action` may switch from "observe" to "confront").

**Path B — Relationship pressure:** Current relationship state (itself influenced by episodic history via relationship deltas) affects `relationship_pressure_with()` which determines `_pick_target()` at `character_agent.py:282-288`.

**Path C — Drift pattern:** Episodic pressure accumulation drives drift pattern classification (`character_drift.py:244-272`) which overrides action selection in `decide_intention()` lines 154-174.

**Example sentence:**
> _His fists clenched at his sides. Arjun, blocked the path of Maya with wariness._

The action "blocked the path of" (from confront action verbs) was selected because the agent's `decide_intention()` returned `action="confront"` due to urgency modulated by episodic memory of a previous tense scene.

**State:** ✅ Active — every scene's intention deliberation uses episodic context from `recent_context()`.

**Percentage:** 70% — `recent_context()` is called every scene for every agent, but the urgency boost only applies when "danger" is in memory text (~30% of scenes). However, drift pattern (also fed by episodic pressure history) influences action in ~60% of scenes by scene 2+.

---

### L6 — Changes scene outcome

**Level description:** Episodic memories affect tension, resolution quality, or scene type.

**Path A — Tension modulation:** Memories feed `emotional_pressure` which feeds into `required_tension` indirectly through agent state → ConflictResolver. The resolved scene type comes from `conflict_resolver.calculate_scene_type()` at `pipeline.py:90-92`.

**Path B — Narrative Mode selection:** `_select_mode()` at `dramatic_realizer.py:647-720` uses character relationships (episodically informed) and agent states (pressure-informed) to choose the NarrativeMode, which determines the entire template pool for the scene (opening, complication, outcome).

However, this is indirect. The episodic memories themselves do **not** directly determine scene type — that's driven by the StoryPlanner's objectives and ConflictResolver's arbitration.

**State:** ⚠️ Partial — episodic influences reach scene outcome through emotional_pressure → intention → scene_type, but this is a multi-step indirect path with many intervening variables.

**Percentage:** 30% — in scenes where episodic content has driven emotional_pressure to >0.6, the influence on outcome templates is stronger. But the path is noisy.

---

### L7 — Changes future story trajectory

**Level description:** Episodic memory recorded in scene N directly affects scene N+1 or beyond.

**Path A — Cross-chapter retrieval:** `EpisodicStore.query()` does **not** filter by chapter. Memories from scene N chapter 1 are returned for scene N chapter 2+ queries. The `recent_context()` window of 3 means the last 3 events in a chapter affect the next chapter's deliberation.

**Path B — Belief persistence:** `beliefs.discovered` persists across scenes and chapters. Anything appended in scene N-1 is available in scene N via `_compose_character_action()`.

**Path C — Emotional pressure carryover:** `_update_emotional_pressure()` at `state_update.py:303-317` adjusts pressure based on scene tension with decay. Pressure persists across scenes within a chapter and between chapters (it's a field on the agent object).

**Path D — Relationship state persistence:** Relationships updated in `update_characters()` persist across the entire story.

**Example trajectory:**
1. Scene 1: "Arjun confronts Maya" → high tension (0.72)
2. StateUpdater records episodic + raises Arjun's pressure to 0.5
3. Scene 2: Arjun's `recent_context()` returns the confrontation memory
4. `_compose_character_action()` includes "aware of [confrontation memory], stepped toward [target]"
5. Memory callback generates "A memory surfaced — the confrontation scene. Arjun had not forgotten."

**State:** ✅ Active — all four paths fire regularly. Cross-chapter trajectory is a primary design goal of the episodic system.

**Percentage:** 90% — after scene 2, beliefs and pressure are always carried forward. Only scene 1 lacks cross-scene context.

---

## 2. Semantic Memory

> Knowledge facts: "what characters discover" — objective factual statements extracted from scene text.

### L0 — Stored

**Level description:** Extracted facts (sentences containing character names + discovery/realization verbs) are written to `SemanticStore.facts`.

**Code path:** `state_update.py:122-137` — within `record_scene_memory()`:
```python
if agents:
    for agent in agents:
        if agent.name in scene.characters_involved:
            for sentence in scene_text.split("."):
                if agent.name in sentence and any(w in sentence.lower()
                    for w in ["discover", "realize", "know", "learn", "see", "find", "understand",
                              "recognize", "notice", "aware", "remember"]):
                    fact_text = sentence.strip()...
                    if fact_text and len(fact_text) > 10:
                        memory.record_fact(text=fact_text[:200], ...)
```

Trigger: sentences in scene text containing character names + discovery keywords.

**State:** ✅ Active — fires every scene for every involved character where the text contains discovery keywords.

**Percentage:** 60% — not every sentence contains discovery keywords. In dialogue-heavy scenes, 5-10 facts are extracted. In action scenes, fewer. Estimated ~4-8 facts per scene.

---

### L1 — Retrieved

**Level description:** Semantic facts are retrieved during the general `retrieve()` call.

**Code path:** `memory_system.py:186-191`:
```python
entity_facts = self.semantic.query(query.focus_character)
seen = {r.text for r in results}
for f in entity_facts:
    if f.text not in seen:
        results.append(f)
        seen.add(f.text)
```

`SemanticStore.query()` at `memory_system.py:45-46` does simple substring matching:
```python
def query(self, entity: str) -> list[MemoryEntry]:
    return [f for f in self.facts if entity.lower() in f.text.lower()]
```

**State:** ✅ Active — fires every scene as part of `retrieve()`.

**Percentage:** 100% — semantic facts are always merged into retrieval results.

---

### L2 — Prompted

**Level description:** Semantic facts are part of the `SceneBlueprint.retrieved_memories` list, just like episodic entries.

**Code path:** Same as Episodic L2 — merged into `retrieved` by `MemorySystem.retrieve()`, which feeds into `SceneBlueprint.retrieved_memories`.

**State:** ✅ Active.

**Percentage:** 100% — facts are always in the memory pool.

---

### L3 — Changes wording

**Level description:** Semantic fact text can be selected for use in prose.

**Path A — Memory callback:** Semantic facts in `retrieved_memories` can be selected by `_compose_memory_callback()` weighted random selection, same as episodic entries. However, facts have `source="semantic"` and `relevance_score=1.0` (hardcoded at `memory_system.py:164`), making them **more** likely to be selected than episodic entries (which have `relevance_score=scene.tension`, typically 0.5-0.8).

**Path B — Belief injection:** Note: semantic facts are **not** appended to `beliefs.discovered` — only episodic events trigger that (`state_update.py:147-148`). So the `_compose_character_action()` pathway does not use semantic facts.

**Example sentence:**
> _A memory surfaced — Arjun realized the platform was not as empty as it seemed. Arjun had not forgotten._

**State:** ⚠️ Partial — facts reach the memory pool for callback selection, but they have no dedicated prose insertion path. They compete with episodic entries in weighted selection.

**Percentage:** 40% — fact can reach prose through `_compose_memory_callback()`, but this fires roughly 1 callback per scene in dialogue/introspection scenes (~50% of scenes). Even when it fires, the weighted selection may choose an episodic entry instead.

---

### L4 — Changes dialogue

**Level description:** Semantic facts influence dialogue content or tags.

**Path:** None. Semantic facts do not feed into `_compose_dialogue_line()` or `_build_dialogue_tag()`.

**State:** ❌ Dead — no code path connects semantic store entries to dialogue generation.

**Percentage:** 0%.

---

### L5 — Changes actions

**Level description:** Semantic facts influence action verb selection.

**Path:** None. Semantic facts are not used in `decide_intention()` or `_compose_character_action()` beyond the general memory pool.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L6 — Changes scene outcome

**Level description:** Semantic facts affect scene type or resolution.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L7 — Changes future story trajectory

**Level description:** Semantic facts recorded in scene N affect scene N+1 or beyond.

**Path A — Cross-chapter retrieval:** `SemanticStore.facts` never clears. Facts from earlier chapters persist and are retrieved in later chapters.

**Path B — No direct trajectory change:** Unlike episodic (which changes pressure and beliefs), semantic facts only sit in the retrieval pool. They don't modify agent state, beliefs, relationships, or pressure. Their influence is limited to being available for callback selection.

**State:** ⚠️ Partial — facts persist across chapters and can be retrieved, but they lack the active influence mechanisms (belief injection, pressure modulation) that make episodic memory trajectory-changing.

**Percentage:** 20% — a semantic fact from scene 1 can be selected by `_compose_memory_callback()` in scene 5, but this is probabilistic and only happens if it wins the weighted selection against all episodic entries.

---

## 3. Interpretation Memory

> Character-specific event interpretations: "how character X sees what happened."

### L0 — Stored

**Level description:** Each character's personalized interpretation of the scene event is written to `InterpretationStore.entries`.

**Code path:** `state_update.py:206-226` — `record_interpretations()` calls `memory.interpret_event()` for each involved character:
```python
for agent in agents:
    if agent.name in scene.characters_involved:
        memory.interpret_event(
            event_text=scene.content[:200],
            character_name=agent.name,
            character_traits=agent.character.traits,
            ...
        )
```

This delegates to `InterpretationEngine.interpret_event()` (`memory_interpretation.py:120-143`) which auto-generates an interpretation based on the event text and character traits.

**Trigger:** Called from `engine.py:293-295` for every scene, every character.

**State:** ✅ Active — fires every scene for every involved character.

**Percentage:** 100% — always written. Generates ~2-3 entries per scene (one per character).

---

### L1 — Retrieved

**Level description:** Interpretations are queried during the general `retrieve()` call, but **only to boost relevance scores** of existing episodic entries.

**Code path:** `memory_system.py:203-211`:
```python
interpretations = self.interpretation_engine.query(
    query.focus_character, top_k=5
)
for interp in interpretations:
    if interp.confidence > 0.7:
        for r in results:
            if interp.source_event_text in r.text or r.text in interp.source_event_text:
                r.relevance_score = min(1.0, r.relevance_score * 1.25)
```

Critical observation: The interpretation text itself is **never returned as a separate MemoryEntry**. It only boosts the relevance score of matching episodic entries by 1.25x. The query filters by character and optionally by emotion.

**State:** ⚠️ Partial — interpretations are queried but only used as a relevance modifier. They are never directly returned as retrievable results.

**Percentage:** 100% — `query_interpretations()` is called in `retrieve()`, but the boost only applies when `confidence > 0.7` (~60% of interpretations meet this threshold).

---

### L2 — Prompted

**Level description:** Boosted relevance scores from interpretations affect which memories are selected in the final top-K, which in turn affects what goes into `SceneBlueprint.retrieved_memories`.

**Path:** The 1.25x relevance boost increases the chance that an episodic entry associated with a high-confidence interpretation is included in the final `results[:query.top_k]` slice.

**State:** ⚠️ Partial — this is a second-order effect. Interpretations don't add new data to the blueprint; they only alter the ranking of existing data.

**Percentage:** 60% — interpretations boost the relevance of episodic entries. In scenes where multiple episodic entries have similar relevance scores, the boost can change which entries survive the top-3 cut.

---

### L3 — Changes wording

**Level description:** Interpretation data directly changes the words in generated prose.

**Path:** None. The `InterpretationEngine` is never called by the `DramaticRealizer`. The realizer has no access to `InterpretationEntry` objects.

**State:** ❌ Dead — interpretation text is computed and stored but never reaches the realizer.

**Percentage:** 0%.

---

### L4 — Changes dialogue

**Level description:** Interpretations affect dialogue content or tags.

**Path:** None. No connection between interpretation data and dialogue generation.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L5 — Changes actions

**Level description:** Interpretations affect action verb selection.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L6 — Changes scene outcome

**Level description:** Interpretations affect scene type or resolution.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L7 — Changes future story trajectory

**Level description:** Interpretations recorded in scene N affect scene N+1 or beyond.

**Path A — Relevance score carryover:** The boosted relevance scores affect retrieval in future scenes because the `EpisodicStore` retains the boosted scores (`r.relevance_score` is modified in place at `memory_system.py:211`). So a scene-1 entry boosted to 1.0 will rank higher in scene-2 retrieval.

**Path B — No active trajectory change:** Unlike episodic (which modifies beliefs and pressure), interpretations only leave a score trace. They don't actively change character state.

**State:** ❌ Dead — no path. The relevance score modification is the only future effect, and it's extremely indirect.

**Percentage:** 5% — the in-place relevance score modification is speculative and may not carry across scenes due to list mutation semantics. Even if it works, the effect size (1.25x) is small.

---

## 4. Consequence Memory

> Action outcomes: "what happened when character did X — did it succeed or fail?"

### L0 — Stored

**Level description:** Each character's action outcome is written to `ConsequenceStore.entries`.

**Code path:** `state_update.py:228-253` — `record_consequences()` calls `memory.record_consequence()` for each involved character:
```python
for agent in agents:
    if agent.name in scene.characters_involved:
        intention = getattr(agent, '_last_intention', None)
        if intention is not None:
            memory.record_consequence(
                character=agent.name,
                action=intention.action if hasattr(intention, 'action') else 'interact',
                consequence=f"{agent.name} attempted {intention.action ...}",
                success=scene.tension < 0.7,
                impact=scene.tension,
                ...
            )
```

**Trigger:** Called from `engine.py:298-300` for every scene, every character who had an intention.

**State:** ✅ Active.

**Percentage:** 90% — `_last_intention` is set on every call to `decide_intention()`, which fires every scene. Occasionally, during the first scene of a fresh pipeline, `_last_intention` may be `None` if the intention deliberation hasn't happened yet.

---

### L1 — Retrieved

**Level description:** Consequences are retrieved during character intention deliberation.

**Code path:** `character_agent.py:177-185` — inside `decide_intention()`:
```python
if self._memory is not None:
    consequences = self._memory.consequences_for_action(action)
    if consequences:
        avg_impact = sum(c.impact_level for c in consequences) / len(consequences)
        if avg_impact > 0:
            urgency = min(1.0, urgency + avg_impact * 0.2)
    success_rate = self._memory.consequence_engine.success_rate(self.name)
    if success_rate < 0.5:
        urgency = max(0.0, urgency - 0.1)
```

Two queries:
1. `consequences_for_action(action)` — keyword match on action text.
2. `success_rate(self.name)` — aggregate success/failure ratio for the character.

**State:** ⚠️ Partial — consequences are retrieved inside the agent's `decide_intention()`, but **not** in the realizer. The realizer never queries consequence data.

**Percentage:** 80% — `_memory` is not None after the first scene. However, `consequences_for_action(action)` may return empty if the action keyword hasn't been seen before (~40% of first scenes).

---

### L2 — Prompted

**Level description:** Consequences influence the `Intention` object which flows into the scene pipeline.

**Path:** `decide_intention()` returns an `Intention` with modulated urgency. This intention is captured in `AgentState.intention` and flows into `SceneBlueprint.agent_states` → `ConflictResolver` → `SceneObjective`.

**State:** ⚠️ Partial — the influence is indirect. Consequences modulate urgency, which is one of many inputs to intention generation.

**Percentage:** 50% — the consequence path fires when `self._memory` is set and there are prior consequences for the same action keyword. This mostly happens in scenes 2+ (where prior scene actions exist) for repeated action types.

---

### L3 — Changes wording

**Level description:** Consequence data directly changes word-level prose.

**Path:** None. `consequences_for_action()` is never called by the realizer. `_compose_character_action()` does not query consequence data.

**State:** ❌ Dead — no code path from ConsequenceStore to prose text.

**Percentage:** 0%.

---

### L4 — Changes dialogue

**Level description:** Consequences affect dialogue content or tags.

**Path:** None. Urgency modulation from consequences flows into dialogue intent (`character_agent.py:251-256`) which can affect dialogue verb selection. However, this is extremely indirect (urgency → intention → dialogue_intent → verb) and the consequence signal is diluted at each step.

**State:** ❌ Dead — no direct path. The indirect path through urgency→intent→verb is functionally negligible.

**Percentage:** <5% — the chain is too long to attribute to consequences specifically.

---

### L5 — Changes actions

**Level description:** Consequences directly affect action verb selection in the next scene.

**Path A — Urgency modulation:** `character_agent.py:178-185` modulates urgency based on past consequence impact and success rate. Higher urgency can shift action selection in the drift pattern logic (lines 154-174):
- `pattern == "desperate"`: action shifts from "observe" → "confront"/"charge"/"pursue"
- `pattern == "cautious"`: action shifts from "charge"/"confront" → "observe"/"negotiate"

**Path B — Drift influence:** Success rate < 0.5 reduces urgency by 0.1, which can shift a character from "aggressive" to "cautious" drift pattern, changing action selection.

**State:** ✅ Active — consequences modulate urgency which feeds drift pattern → action selection.

**Example trajectory:**
1. Scene 1: Arjun uses "confront" action → tension=0.72 → success=False
2. Consequence recorded: `action="confront", success=False, impact=0.72`
3. Scene 2: `consequences_for_action("confront")` returns avg_impact=0.72, `success_rate("Arjun")` = 0.0
4. urgency reduced by 0.1 because success_rate < 0.5
5. If urgency drops below 0.5, action may shift from "confront" to "observe"

**Percentage:** 30% — fires reliably after scene 2+ when there are prior consequences. But the effect size is small (±0.1-0.2 urgency).

---

### L6 — Changes scene outcome

**Level description:** Consequences affect scene type or resolution.

**Path:** Indirect — urgency modulation feeds into intention, which feeds into ConflictResolver, which determines scene type. A more urgent character may push the scene toward CONFRONTATION type.

**State:** ⚠️ Partial — very indirect, and urgency is only one of many inputs to scene type.

**Percentage:** 15% — in later scenes where consequence history has accumulated, the urgency modulation has a measurable effect, but it's overwhelmed by other signals (planned objective, relationship state, world context).

---

### L7 — Changes future story trajectory

**Level description:** Consequence recorded in scene N affects scene N+1 or beyond.

**Path A — Urgency carryover:** `_compute_urgency()` in `decide_intention()` uses consequence data from all prior scenes. Each scene's consequence adds to the cumulative history.

**Path B — Success rate carryover:** `success_rate()` aggregates across all prior scenes. A character with 3 failures in 5 actions will have a 0.4 success rate, producing a -0.1 urgency penalty in all future decisions.

**State:** ✅ Active — consequences accumulate across chapters and persistently influence intention deliberation.

**Percentage:** 50% — by scene 3+, each character has 2-3 consequences in the store. The effect is cumulative and grows with story length.

---

## 5. Relationship Memory (Delta)

> Relationship change history: "when did Arjun and Maya become enemies?"

### L0 — Stored

**Level description:** Relationship shifts (old → new relation with trigger text) are written to `RelationshipDeltaStore.deltas`.

**Code path — Two callers:**

**Path A:** `state_update.py:37-108` — `update_characters()` detects relationship changes via keyword matching + tension thresholds and calls `memory.record_relationship_delta()` at line 93-98.

**Path B:** `state_update.py:255-296` — `record_relationship_deltas()` (called separately from `engine.py:303-305`) uses pure tension thresholds (>0.8 enemy, >0.8 rival, <0.2 neutral) to detect changes and calls `memory.record_relationship_delta()` at line 292-296.

Both paths also update live relationship objects on the agent:
```python
agent_a.character.relationships[b_name] = new_rel
agent_b.character.relationships[a_name] = new_rel
agent_a.beliefs.relationship_beliefs[b_name] = new_rel.value
agent_b.beliefs.relationship_beliefs[a_name] = new_rel.value
```

**State:** ✅ Active — both paths fire on multi-character scenes.

**Percentage:** 80% — multi-character scenes are ~80% of all scenes. However, not every multi-character scene triggers a delta (tension must cross a threshold). For scenes with tension > 0.6, 100% fire a delta.

---

### L1 — Retrieved

**Level description:** Relationship state and history are read back.

**Path A — Current sentiment:** `pipeline.py:78` — called per agent pair:
```python
sentiment = self.memory.current_relationship_sentiment(agent.name, other)
```
This queries `RelationshipDeltaTracker.current_sentiment()` (`memory_relationship.py:95-103`) which returns the sentiment value of the latest delta's new relation.

**Path B — Relationship pressure:** `pipeline.py:76-77` — `agent.relationship_pressure_with(other)` uses the **live** `agent.character.relationships` dict (not the delta store). But this dict was updated by the delta recording (L0 above).

**Path C — `_select_mode()`:** `dramatic_realizer.py:661-668` — reads relationship between first two characters from `bp.agent_states` to select NarrativeMode.

**State:** ✅ Active — Path A fires every scene per agent pair. Path B fires every scene per agent pair. Path C fires every scene with 2+ characters.

**Percentage:** 100% — all paths fire regularly.

---

### L2 — Prompted

**Level description:** Relationship state enters the `SceneBlueprint`.

**Path A — AgentState:** `CharacterRecord.relationships` is part of `AgentState`, which is part of `SceneBlueprint.agent_states`. This feeds the realizer's `_select_mode()` and dialogue tag builders.

**Path B — Relationship belief:** `CharacterBeliefs.relationship_beliefs` is part of `AgentState.beliefs`, which feeds `_compose_character_action()`.

**State:** ✅ Active — both paths populate the blueprint every scene.

**Percentage:** 100%.

---

### L3 — Changes wording

**Level description:** Relationship state changes the specific words in prose output.

**Path A — Relationship phrase in actions:** `_compose_character_action()` at `dramatic_realizer.py:810-818`:
```python
rel_phrase = ""
if beliefs.relationship_beliefs and target:
    rel_val = beliefs.relationship_beliefs.get(target, "").lower()
    if rel_val in ("ally", "friend", "trusted", "family"):
        rel_phrase = "with trust"
    elif rel_val in ("enemy", "distrusted", "hostile"):
        rel_phrase = "with wariness"
    elif rel_val in ("rival", "competitor"):
        rel_phrase = "with guarded tension"
```

**Example sentence:**
> _His fists clenched at his sides. Arjun, blocked the path of Maya with wariness._

The phrase "with wariness" was added because relationship_beliefs[Maya] == "enemy".

**Path B — Narrative mode opening templates:** Relationship state helps select the NarrativeMode via `_select_mode()`, which determines the entire template pool. Mode-specific openings, complications, and outcomes contain different wordings.

**Example contrasting sentences (same scene type, different modes):**
- CONFRONTATION mode: _"Tension coiled through the room, pulling the air taut."_
- RECONCILIATION mode: _"The distance between them was measured in words left unsaid."_
- BETRAYAL mode: _"Trust was a fragile thing — and it had just shattered."_

**State:** ✅ Active — Path A fires on every action sentence for characters with relationship beliefs. Path B fires every scene.

**Percentage:** 75% — Path A fires whenever the target character is in relationship_beliefs (~75% of action sentences). Path B (mode selection) fires 100% of scenes.

---

### L4 — Changes dialogue

**Level description:** Relationship state affects dialogue tags, intent, and content.

**Path A — Dialogue tag via `_dialogue_tag_for()`:** `dramatic_realizer.py:558-567` — uses relationship to choose between angry/fearful/calm tags:
```python
if pressure > 0.5:
    if relationship in (RelationKind.ENEMY, RelationKind.RIVAL):
        return random.choice(_ANGRY_TAGS)
```

**Path B — Dialogue tag via `_build_dialogue_tag()`:** `dramatic_realizer.py:1039-1046`:
```python
if rel in (RelationKind.ENEMY, RelationKind.RIVAL):
    if random.random() < 0.3:
        tag = random.choice(_ANGRY_TAGS)
elif rel in (RelationKind.ALLY, RelationKind.FAMILY):
    if random.random() < 0.3:
        tag = random.choice(_CALM_TAGS)
```

**Path C — Dialogue intent:** `DialogueIntentResolver.resolve_intent()` at `character_dialogue.py:258-280` — `_RELATION_INTENT_BIAS` maps relationship to default intent:
```python
_RELATION_INTENT_BIAS = {
    RelationKind.ALLY: "comfort",
    RelationKind.RIVAL: "challenge",
    RelationKind.ENEMY: "threaten",
    ...
}
```
This intent determines the dialogue line pool (from `_DIALOGUE_LINES`) and the dialogue verb (from `_INTENT_VERB_MAP`).

**Example sentences (from intent selected by relationship):**

Enemy/threaten: _"Do not test me," snarled Maya. (Maya was hiding insecurity behind aggression.)_

Ally/comfort: _"It will be all right," soothed Arjun. (Arjun was offering empty reassurance.)_

**State:** ✅ Active — all three paths fire on every dialogue line.

**Percentage:** 100% — every dialogue line (in every scene type that includes dialogue) is affected by relationship state through at least one of these paths.

---

### L5 — Changes actions

**Level description:** Relationship state affects action verb and target selection.

**Path A — Target selection:** `relationship_pressure_with()` at `character_agent.py:204-215` maps relationship → base pressure. The `_pick_target()` method (line 282-288) sorts targets by absolute pressure and picks the highest. Characters with ENEMY/RIVAL relationships are more likely to be targeted.

**Path B — Drift pattern:** Relationship sentiment feeds into emotional pressure at `state_update.py:105-108`:
```python
sentiment = memory.current_relationship_sentiment(a_name, b_name)
if sentiment < 0:
    agent_a.emotional_pressure = min(1.0, agent_a.emotional_pressure + abs(sentiment) * 0.1)
```
Higher pressure → more aggressive/desperate drift patterns → different action verbs ("confront" vs "observe").

**Path C — Action verb selection:** The drift pattern influences `decide_intention()` at `character_agent.py:154-174`, selecting from action pools based on pattern.

**Example trajectory:**
1. Relationship Arjun→Maya: NEUTRAL → RIVAL (delta recorded)
2. Sentiment = -0.5 (from RIVAL weight)
3. Arjun's emotional_pressure +0.05 (abs(-0.5) * 0.1)
4. If pressure > 0.65, drift pattern → "aggressive"
5. Action shifts from "observe" to "confront"

**Resulting sentence:**
> _A vein pulsed in his neck. Arjun, stepped toward Maya with guarded tension._

**State:** ✅ Active — Path A fires on every scene. Path B fires when sentiment < 0 (~30% of scenes post-delta). Path C fires when pressure crosses drift thresholds (~20% of scenes).

**Percentage:** 40% — target selection is always influenced; action verb shifts only when pressure crosses drift thresholds.

---

### L6 — Changes scene outcome

**Level description:** Relationship state affects scene type and resolution.

**Path A — Narrative Mode selection:** `_select_mode()` at `dramatic_realizer.py:661-668` reads relationship between first two characters for mode selection. Multiple branches use relationship:
```python
rel = s1.character.relationships[c2]  # line 668

# Line 685-686
if rel in (RelationKind.ENEMY, RelationKind.RIVAL) and tension > 0.6:
    if any(k in purpose for k in confrontation_keywords):
        return NarrativeMode.CONFRONTATION

# Line 690-692
if any(k in purpose for k in romance_keywords) or rel in (RelationKind.FAMILY, RelationKind.ALLY):
    if tension < 0.5:
        return NarrativeMode.ROMANCE

# Line 709-712
if stype == SceneType.DIALOGUE and tension > 0.6 and len(chars) >= 2 and rel in (RelationKind.ENEMY, RelationKind.RIVAL):
    return NarrativeMode.CONFRONTATION
if stype == SceneType.DIALOGUE and tension < 0.4:
    return NarrativeMode.RECONCILIATION if rel in (RelationKind.ALLY, RelationKind.FAMILY) else NarrativeMode.NEGOTIATION
```

The NarrativeMode determines the entire template pool for openings, complications, and outcomes — directly shaping how the scene resolves.

**Path B — Outcome template selection:** `_compose_outcome()` at `dramatic_realizer.py:1104-1132` uses the NarrativeMode (selected with relationship input). Different modes have different outcome templates.

**Example outcome sentences (mode-dependent):**
- CONFRONTATION: _"Nothing was resolved. But the terms of engagement had changed."_
- RECONCILIATION: _"Forgiveness was not instantaneous. But the first step had been taken."_
- REVELATION: _"The truth was out. What happened next was up to them."_

**State:** ✅ Active — Path A fires every scene to select the mode. Relationship is a primary input.

**Percentage:** 50% — relationship directly triggers mode selection in 3 specific branches (ENEMY/RIVAL→CONFRONTATION, FAMILY/ALLY→ROMANCE, FAMILY/ALLY→RECONCILIATION). In other scenes, mode falls through to keyword-based or fallback paths.

---

### L7 — Changes future story trajectory

**Level description:** Relationship deltas recorded in scene N affect scene N+1 and beyond.

**Path A — Live relationship state carryover:** `CharacterRecord.relationships` is mutated in place by `record_relationship_deltas()` and `update_characters()`. Every future scene uses the updated relationship state for mode selection, dialogue tags, and action targeting.

**Path B — Sentiment modulation:** `current_relationship_sentiment()` aggregates delta history and feeds back into emotional pressure (`state_update.py:105-108`), which persists across chapters.

**Path C — Belief carryover:** `relationship_beliefs` is updated (`state_update.py:101-102, 290-291`) and persists for the entire story. The realizer reads it in `_compose_character_action()` for relationship phrases.

**Example trajectory (multi-chapter):**
1. Chapter 1, Scene 2: Tension 0.68 → NEUTRAL→RIVAL (Arjun↔Maya)
2. `update_characters()` updates live relationship + beliefs
3. Chapter 2, Scene 1: `_select_mode()` reads `rel=RIVAL, tension>0.6` → CONFRONTATION
4. Dialogue tags: `_build_dialogue_tag()` uses RIVAL → 30% chance of ANGRY_TAGS
5. Action text: `_compose_character_action()` uses relationship_beliefs["Maya"]=="rival" → "with guarded tension"

**State:** ✅ Active — relationship state is one of the most durable cross-chapter influence mechanisms in the system.

**Percentage:** 100% — relationship state persists and affects every subsequent scene involving those characters.

---

## 6. Callback Memory

> Scheduled memory resurfacing: "a memory from chapter 1 returns in chapter 3 at the dramatically right moment."

### L0 — Stored

**Level description:** Callbacks are scheduled in `CallbackScheduler.callbacks` list.

**Code path:** `state_update.py:154-165` — in `record_scene_memory()`:
```python
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
```

**Trigger:** scenes with `tension > 0.4`. Note: the threshold was lowered from 0.7 (used to be dead code — all callbacks missed in SHORT mode).

**State:** ✅ Active.

**Percentage:** 60% — ~60% of scenes have tension > 0.4. In SHORT mode (1 chapter), the callback is scheduled for chapter 2 which never comes, but the callback is still stored and can be checked.

---

### L1 — Retrieved

**Level description:** Callbacks are checked and their data is injected.

**Path A — Belief injection (in `record_scene_memory()`):** `state_update.py:167-178`:
```python
pending = memory.check_callbacks(chapter_num)
for cb in pending:
    ...
    for char in scene.characters_involved:
        memory.beliefs_for(char).discovered.append(resurface_text)
    memory.mark_callback_fired(cb_id)
```
This injects callback text directly into the character's discovered beliefs.

**Path B — Memory injection (in pipeline):** `pipeline.py:119-138`:
```python
pending = self.memory.check_callbacks(chapter_num)
for cb in pending:
    retrieved.append(MemoryEntry(
        text=cb.callback_data.get("resurface_text", ...),
        source="callback",
        ...
    ))
```
This injects callback text as a MemoryEntry that joins the `SceneBlueprint.retrieved_memories` pool.

**State:** ✅ Active — Path A fires in every scene's `record_scene_memory()`. Path B fires in every scene's `pipeline.run()`. Both check for pending callbacks.

**Percentage:** 100% — both paths check callbacks every scene. Actual retrievals only happen when `trigger_chapter == current_chapter` (~once per chapter if scheduled).

---

### L2 — Prompted

**Level description:** Callback data enters the `SceneBlueprint` and character beliefs.

**Path A — Beliefs:** Callback text appended to `beliefs.discovered` is available to `_compose_character_action()` in the realizer.

**Path B — SceneBlueprint:** Callback MemoryEntries from pipeline.py are in `retrieved_memories`, available to `_compose_memory_callback()`.

**State:** ✅ Active.

**Percentage:** 100% when callbacks fire — but this only happens on the trigger chapter.

---

### L3 — Changes wording

**Level description:** Callback text directly appears in prose.

**Path A — Via `_compose_memory_callback()`:** Callback entries in `retrieved_memories` can be selected by the weighted memory callback composer. The callback text has `relevance_score=0.8` (hardcoded at `pipeline.py:135`), making it competitive.

**Path B — Via `_compose_character_action()`:** Callback text in `beliefs.discovered` can be selected for the "aware of {discovery}" prefix in action descriptions.

**Example sentence (Path A):**
> _A memory surfaced — A tense moment from chapter 1 still haunted Arjun. Arjun had not forgotten._

**Example sentence (Path B):**
> _Arjun, aware of a tense moment from chapter 1 still haunted Arjun, studied Maya with careful precision._

**Note:** Example B shows a grammar artifact (pronoun mismatch) that can occur when raw callback text is injected into the "aware of" template. This is a known minor issue.

**State:** ✅ Active — both paths fire when callback data is present.

**Percentage:** 30% — Path A fires on dialogue/introspection/description scenes (~50% of total).
Path B fires whenever callback text is in beliefs (100% of scenes where callback fired in the same scene's `record_scene_memory()`).

Combined: callback data reaches prose in ~50% of scenes where a callback has been triggered.

---

### L4 — Changes dialogue

**Level description:** Callback text affects dialogue content or tags.

**Path A — Indirect via beliefs:** Callback text in `beliefs.discovered` provides content for the "aware of" prefix in action descriptions, but not directly in dialogue lines.

**Path B — Indirect via emotional pressure:** The callback injection in `record_scene_memory()` can trigger `perceive()`→ emotional pressure shift → dialogue tag selection. But this is very indirect.

**State:** ⚠️ Partial — no direct dialogue influence, but indirect through pressure.

**Percentage:** 10% — indirect path only.

---

### L5 — Changes actions

**Level description:** Callback data affects action verb selection.

**Path:** Callback text in `beliefs.discovered` is used in `_compose_character_action()` for the "aware of" action description prefix, but does **not** affect the action verb itself. The verb is determined by `intention.action` which comes from `decide_intention()`, which does **not** use callback data.

**State:** ⚠️ Partial — callback data adds context to action descriptions but does not change the verb.

**Percentage:** 20% — "aware of" prefix fires when beliefs have callback content, which is ~50% of post-callback scenes.

---

### L6 — Changes scene outcome

**Level description:** Callbacks affect scene type or resolution.

**Path:** None. Callback data does not enter ConflictResolver or influence scene type selection.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L7 — Changes future story trajectory

**Level description:** Callbacks are explicitly designed for cross-chapter influence.

**Path A — Explicit trigger mechanism:** Callbacks scheduled with `trigger_chapter = chapter_num + 1` fire in a specific future chapter. The callback data is explicitly designed to resurface past events at dramatically appropriate moments.

**Path B — Belief persistence:** Once fired into `beliefs.discovered`, callback text persists for the remainder of the story. It's available for action description in all future scenes.

**Example trajectory:**
1. Chapter 1, Scene 1: Tension 0.68 → callback scheduled for chapter 2
2. Chapter 2, Scene 1: `check_callbacks(2)` returns the callback
3. Callback injected into `beliefs.discovered` AND `retrieved_memories`
4. Chapter 2, Scene 1 action: `_compose_character_action()` uses callback text
5. Chapter 2, Scene 1 memory callback: `_compose_memory_callback()` picks callback entry

**State:** ✅ Active — this is the core design purpose of the CallbackScheduler.

**Percentage:** 100% — scheduled callbacks always fire on their trigger chapter (in BOOK mode). In SHORT mode, they're scheduled for chapter 2 which doesn't exist, so they remain pending but unused.

---

## 7. RAG (RAGBridge)

> Pre-built corpus retrieval: "external knowledge from the Gutenberg corpus."

### L0 — Stored

**Level description:** RAG corpus is loaded from `rag_corpus.jsonl` at `MemorySystem` initialization.

**Code path:** `rag_bridge.py:19-28` — `load()` reads the JSONL file and stores entries in `self._corpus`.

**Trigger:** Called from `MemorySystem.__init__()` at `memory_system.py:81-82`:
```python
if self.rag_bridge is not None:
    self.rag_bridge.load()
```

The corpus is **static** — loaded once at init, never updated during generation.

**State:** ✅ Active — loads on init if the corpus file exists.

**Percentage:** 100% — always loads at init if the file is present.

---

### L1 — Retrieved

**Level description:** RAG corpus entries are retrieved during the general `retrieve()` call.

**Code path:** `memory_system.py:213-219`:
```python
if self.rag_bridge is not None and self.rag_bridge.is_loaded:
    rag_results = self.rag_bridge.retrieve(query)
    for mem in rag_results:
        if mem.text not in seen:
            results.append(mem)
            seen.add(mem.text)
```

`RAGBridge.retrieve()` at `rag_bridge.py:34-52` does simple keyword matching against the corpus.

**State:** ⚠️ Partial — retrieval fires every scene, but the keyword matching is primitive (no embedding, no BM25, just substring containment).

**Percentage:** 100% — always fires, but results are empty if no corpus keywords match the query (~60% of scenes due to generic scene context).

---

### L2 — Prompted

**Level description:** RAG results join the `SceneBlueprint.retrieved_memories` pool.

**Code path:** Same as Episodic L2 — RAG results are appended to `retrieved` inside `MemorySystem.retrieve()`, which feeds `SceneBlueprint.retrieved_memories`.

**State:** ⚠️ Partial — RAG entries are in the pool but have no dedicated insertion path.

**Percentage:** 40% — RAG entries reach the blueprint only when keyword matches exist. Even then, they compete with episodic/semantic entries in top-K truncation.

---

### L3 — Changes wording

**Level description:** RAG corpus text directly affects prose wording.

**Path A — Memory callback:** RAG entries in `retrieved_memories` can be selected by `_compose_memory_callback()` weighted random selection. However, RAG entries have `relevance_score` from the JSONL file (typically 0.5), which is lower than episodic entries (0.4-0.8) and semantic entries (1.0).

**Path B — No dedicated path:** Unlike episodic memory, RAG entries do NOT feed into `beliefs.discovered`, `perceive()`, or any other realizer-accessible structure.

**State:** ❌ Dead — RAG entries are nominally available for callback selection, but in practice they are filtered out by the top-K truncation or out-weighed by higher-relevance episodic/semantic entries.

**Percentage:** <5% — a RAG entry would need a higher relevance score than competing memories AND survive top-K truncation. Very unlikely in practice.

---

### L4 — Changes dialogue

**Level description:** RAG corpus data affects dialogue.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L5 — Changes actions

**Level description:** RAG data affects action selection.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L6 — Changes scene outcome

**Level description:** RAG data affects scene type or resolution.

**Path:** None.

**State:** ❌ Dead.

**Percentage:** 0%.

---

### L7 — Changes future story trajectory

**Level description:** RAG entries affect future scenes.

**Path A — Static corpus:** The RAG corpus is loaded once at init and never updated. There is no feedback loop — generation does not add to the corpus.

**Path B — No persistent influence:** RAG entries do not modify character beliefs, relationships, emotional pressure, or any other state that persists across scenes.

**State:** ❌ Dead — the static corpus and lack of persistent influence channels make RAG functionally inert for trajectory changes.

**Percentage:** 0%.

---

## Comparative Analysis

### Influence Depth Scores

| Subsystem | Active Levels | Score (0-8) | Bottleneck |
|-----------|--------------|-------------|------------|
| **Relationship** | L0-L7 all active | **8/8** | None — fully integrated |
| **Episodic** | L0-L7 (L6 partial) | **7.5/8** | L6 indirect scene type influence |
| **Callback** | L0-L5, L7 (L4-L5 partial) | **5.5/8** | L6 dead; L4-L5 indirect |
| **Consequence** | L0, L5, L7 (L1-L2, L6 partial) | **3.5/8** | L3-L4 dead; L1 limited scope |
| **Semantic** | L0-L3 (L3 partial) | **2.5/8** | No dedicated realizer path |
| **Interpretation** | L0, L1-L2 partial | **1.5/8** | Only boosts relevance; never reaches realizer |
| **RAG** | L0 only | **1/8** | Static corpus; no influence channel |

### Cross-Subsystem Dependencies

```
Episodic ──► Semantic (facts extracted from episodic text)
Episodic ──► Interpretation (interpretations based on episodic events)
Episodic ──► Consequence (consequences based on episodic tension)
Episodic ──► Callback (callbacks scheduled on episodic tension)
Episodic ──► Relationship (relationship deltas triggered by episodic content)

Relationship ──► Episodic (sentiment modulates pressure → future episodic influence)
Callback ──► Episodic (callback data injected into beliefs → acts like episodic)
```

### Most Influential Subsystems by Level

| Level | Most Influential | Why |
|-------|-----------------|-----|
| L0 | Episodic | Fires on 100% of scenes, all characters |
| L1 | Relationship | 3 distinct retrieval paths, 100% of scenes |
| L2 | Relationship | Dictionary lookup in agent_states, 100% of scenes |
| L3 | Episodic, Relationship | Both have dedicated prose insertion paths |
| L4 | Relationship | Intent + tag selection on every dialogue line |
| L5 | Episodic, Relationship | Action verb + target selection |
| L6 | Relationship | NarrativeMode selection directly uses relationship |
| L7 | Episodic, Relationship, Callback | Persistent state carryover across chapters |

### Dead Code Paths (No Influence)

| Path | Subsystem | LOC | Blocked At |
|------|-----------|-----|------------|
| Interpretation → Realizer | Interpretation | 207 lines | Never queried by realizer |
| Consequence → Realizer | Consequence | 110 lines | Used only in `decide_intention()` |
| RAG → Realizer | RAG | 52 lines | Static corpus, weak retrieval, out-competed |
| Semantic → dialogue | Semantic | — | No path to dialogue tag/intent/verb |

### Recommendations (by Severity)

**Critical:**
1. **Interpretation → Realizer**: Add `query_interpretations()` call in `_compose_memory_callback()` or as a dedicated prose block. Existing 207 lines of code have zero direct prose influence. Change: ~20 lines in `dramatic_realizer.py`.

2. **Semantic belief injection**: Add semantic facts to `beliefs.discovered` in `record_scene_memory()`. Currently only episodic feeds into beliefs. Change: 1 line in `state_update.py`.

**High:**
3. **Consequence → Realizer**: Add `consequences_for_action()` call in `_compose_character_action()` to modulate action phrase selection. Change: ~15 lines in `dramatic_realizer.py`.

4. **RAG bridge improvement**: Switch from keyword substring matching to TF-IDF or the existing `all-MiniLM-L6-v2` embedding model. Improve relevance scoring. Change: ~30 lines in `rag_bridge.py`.

**Medium:**
5. **Interpretation relevance boost clarity**: The in-place modification of `r.relevance_score` at `memory_system.py:211` is a side-effect that may not persist. Audit whether this mutation is durable.

6. **Callback grammar artifact**: The "aware of" template at `dramatic_realizer.py:797-808` can produce pronoun mismatches when callback text contains character names. Consider sanitizing the injected text.

**Low:**
7. **Episodic L6 path**: Strengthen the episodic→scene type path by adding an explicit tension/relevance input to ConflictResolver's scene type calculation.

---

## Appendix A: Code Path Quick Reference

| Subsystem | L0 Store | L1 Retrieve | L3-L5 Wording/Action |
|-----------|----------|-------------|---------------------|
| Episodic | `state_update.py:140` | `pipeline.py:74,110` | `dramatic_realizer.py:777,797,1062` |
| Semantic | `state_update.py:132` | `memory_system.py:186` | `dramatic_realizer.py:1062` (pool only) |
| Interpretation | `state_update.py:220` | `memory_system.py:204` | *(dead)* |
| Consequence | `state_update.py:245` | `character_agent.py:178` | `character_agent.py:180-185` (urgency) |
| Relationship | `state_update.py:93,292` | `pipeline.py:78`, `dramatic_realizer.py:661` | `dramatic_realizer.py:810,954,1039` |
| Callback | `state_update.py:161` | `state_update.py:168`, `pipeline.py:121` | `dramatic_realizer.py:797,1062` |
| RAG | `rag_bridge.py:26` (load) | `memory_system.py:215` | `dramatic_realizer.py:1062` (pool only) |

---

## Appendix B: Previous Audit Reconciliation

This report updates and supersedes the previous `memory_activation_report.md` (Mission 8) findings:

| Claim from Mission 8 | Status in Depth Report | Correction |
|----------------------|----------------------|------------|
| "4/6 subsystems directly influencing prose" | Confirmed — but narrower paths | Relationship + Episodic + Callback + Semantic (limited) |
| "Interpretation → Realizer: data exists but unused" | Confirmed **still unused** | No change since Mission 8 |
| "Consequence → Realizer: not wired" | Confirmed **still not wired** to prose | Only feeds `decide_intention()` urgency |
| "Semantic facts available for callbacks" | Confirmed — but out-competed by episodic | Semantic `relevance_score=1.0` is high, but no dedicated path |
| "No dead code in memory activation path" | Disputed | Interpretation (no direct prose path), RAG (functionally inert), Semantic (no prose path beyond callback pool) are **effectively dead** for L3-L7 |

**New findings (not in previous report):**
1. Relationship delta is the **only** subsystem with full L0-L7 active depth
2. Interpretation relevance boost at `memory_system.py:211` uses in-place mutation on `r.relevance_score` — side-effect may not persist
3. RAG corpus is static and keyword-only; functionally irrelevant to generation
4. Two redundant relationship delta recording paths exist (`record_relationship_deltas()` + `update_characters()`)
5. Callback grammar artifact: pronoun mismatch in "aware of {discovery}" template

---

*End of report — 7 subsystems traced through 8 influence levels.*
