# SCRIPTY v2 — Realizer Redesign

## 1. CompositionalRealizer Audit — Code-Level Diagnosis

### `_compose_setting`
**Produces**: `"The {raw_api_display_name} stretches under the {era} sky, its {infra} standing as markers of a {tone} time. {Transport} trace through the terrain."`
**Why mechanical**: Fixed 3-clause template. Raw API text (Nominatim `display_name`) leaks verbatim. Infrastructure/transport chosen by `random.choice` from static list with no scene-specific logic. Every scene opens identically.

### `_compose_character_entry`
**Produces**: `"{Name}, the {role}, moves with {emotion} purpose — driven to {action} {target} in pursuit of {goal}."`
**Why mechanical**: Em dash exposition. Uses `character.emotional_state` (static "neutral" default) instead of dynamic `emotional_state_str()`. Action verb comes from `_action_for_trait` trait map (1 word). Every character entry follows same grammatical structure.

### `_compose_actions`
**Produces**: `"Tension erupts as {conflict} forces collide — {purpose}."` / `"{Name} faces {Name}, the air thick with {conflict} tension."` / `"Silence surrounds {Name}, the weight of decisions pressing — {purpose}."`
**Why mechanical**: Every scene type (ACTION/DIALOGUE/INTROSPECTION/DESCRIPTION) has exactly 1-2 template strings with zero variation. No actual action verbs, no quoted dialogue, no concrete details. The `— {purpose}` suffix is identical across all types.

### `_compose_reflection`
**Produces**: `"A memory surfaces in {character}'s mind — {mem_text[:100]} — shaping every choice that follows."`
**Why mechanical**: Only fires for DIALOGUE/INTROSPECTION. Memory text is raw truncated first 100 chars. Always same framing "a memory surfaces".

### `_compute_tension_sentence`
**Produces**: One of 3 hardcoded strings depending on tension threshold.
**Why mechanical**: No integration with scene content. Same 3 sentences for every story, every genre, every character.

### `_compose_closing`
**Produces**: `"As the moment passes, the need to {resolution_goal} becomes the only thought."`
**Why mechanical**: Always present. Always same framing. Resolution goal injected without conjugation.

### Structural Diagnosis
| Issue | Root Cause | Line(s) |
|-------|-----------|---------|
| Raw API text | `world.location_description` = Nominatim display_name | 85 |
| No dialogue | `SceneType.DIALOGUE` branch has no quote generation | 128-136 |
| Emotion label not state | Uses `character.emotional_state` not `emotional_state_str()` | 98 |
| Same opening every scene | `_compose_setting` has single template, called every scene | 36, 80-91 |
| Simulation-log prose | Actions are *described* not *enacted* | 117-155 |
| Zero causal chains | No event sequencing, no consequence relationships | 31-78 |
| Static scenes | No beginning/development/change/outcome structure | 31-78 |

---

## 2. Dramatic Event Pipeline

### Current (broken):
```
SceneObjective → Description → Report (simulation-log prose)
```

### New:
```
SceneObjective → Event Chain → Dramatic Scene
```

### Event Chain Structure:
```
Opening Event
  ↓ (causes)
Character Reaction
  ↓ (causes)
Escalation / Complication
  ↓ (causes)
Counteraction
  ↓ (causes)
Consequence / Outcome
```

### Event Types:
| Event | Description | Content |
|-------|-------------|---------|
| OPENING | Establish location + character presence through action | "Rain hammered the cobblestones as Arjun stepped into the square." |
| ACTION | Character acts on intention | "He grabbed Maya's wrist before she could disappear into the crowd." |
| DIALOGUE | Characters speak with quoted speech | "\"You can't hide forever,\" Arjun said." |
| REACTION | Response to preceding event | "Maya's face went pale. Her hand trembled against the wall." |
| COMPLICATION | New information or obstacle | "A third figure emerged from the fog — one neither of them expected." |
| OUTCOME | Scene ends with change or cliffhanger | "The ledger slipped from his fingers and hit the water. Truth sank with it." |

---

## 3. Dialogue System

### Data Flow:
```
AgentState.intention → SpeechIntent → Dialogue Template → Quoted Speech
AgentState.emotional_pressure → Tone Modifier → Word Choice / Punctuation
CharacterRecord.relationships → Formality → Address / Register
MemoryEntry → Callback → Dialogue Reference
```

### Speech Intent → Dialogue Templates:
| Intent | Templates |
|--------|-----------|
| REVEAL | "\"I know what you did.\"", "\"The truth is...\"" |
| DECEIVE | "\"I don't know what you're talking about.\"", "\"You've got the wrong person.\"" |
| PERSUADE | "\"You have to trust me.\"", "\"Think about what you're doing.\"" |
| THREATEN | "\"If you don't stop, I'll make you.\"", "\"You'll regret this.\"" |
| BEG | "\"Please, I'm asking you.\"", "\"Don't do this.\"" |
| QUESTION | "\"Why are you doing this?\"", "\"What do you know?\"" |
| COMMAND | "\"Stop right there.\"", "\"Tell me what you saw.\"" |
| WARN | "\"You're in danger.\"", "\"Don't trust them.\"" |
| CONFESS | "\"It was me.\"", "\"I have to tell you something.\"" |
| BARGAIN | "\"I'll make you a deal.\"", "\"Let's trade.\"" |

### Emotion → Tone Modifier:
| Emotion | Effect |
|---------|--------|
| high pressure (>0.7) | Short sentences, "I said STOP", harsh verbs |
| medium pressure (0.4-0.7) | Hesitation markers, "I... I don't know" |
| low pressure (<0.2) | Long sentences, calm vocabulary |

### Relationship → Register:
| Relationship | Effect |
|-------------|--------|
| ENEMY | Insults, cold formality, addressing by full name |
| RIVAL | Competitive language, grudging respect |
| ALLY/FAMILY | Warmth, shared references, first names |
| MENTOR | Deference, questions seeking guidance |

---

## 4. Emotion Realization

### Current (broken):
```python
f"{name}, the {role}, moves with {emotion} purpose"
f"{name} grapples with a {thought} thought"
```

### New — Behavioral Expression:

| Emotion | Behavior | Dialogue Marker | Body Language |
|---------|----------|----------------|---------------|
| Angry | Slams fist, advances, invades space | Short words, exclamation | Clenched fists, rigid posture |
| Afraid | Retreats, looks for exit, freezes | Broken sentences, questions | Wide eyes, trembling |
| Sad | Slumps, slows, withdraws | Ellipses, quiet | Averted gaze, heavy steps |
| Joyful | Quick movements, open posture | Exclamation, laughter | Smiling, relaxed shoulders |
| Anxious | Fidgeting, checking, pacing | Repetition, self-interruption | Sweating, darting eyes |
| Desperate | Reckless action, pleading | Begging, bargaining | Grabbing, not letting go |
| Calm | Measured movements, steady gaze | Long sentences, steady tone | Relaxed stance, slow breath |

---

## 5. Show-vs-Tell Layer

### Current (tell):
```
"Arjun moves with neutral purpose — driven to investigate Maya in pursuit of uncover the truth."
"Tension erupts as emerging forces collide."
```

### New (show):
```
"Arjun's eyes locked onto Maya across the courtyard. He stepped forward, weaving through the crowd — never letting her out of his sight."
"The market square fell quiet. Two figures stood at opposite ends, a collapsed cart between them, its owner shouting into the rain."
```

### Mapping:
| Abstract | Concrete |
|----------|----------|
| Goal: uncover the truth | Character searches, asks questions, follows someone |
| Conflict: emerging | Two characters want opposite things, shown through simultaneous action |
| Emotion: angry | Character's hands ball into fists, voice sharpens |
| Intention: investigate | Character moves toward something, kneels, examines |
| Memory: past event | Character freezes, flash of recognition, muttered name |

---

## 6. Event Sequencer

### Every scene follows:
```
[Opening]   → Who, where, when — shown through character action in environment
[Response]  → Character reacts to situation (dialogue or action)
[Change]    → Something shifts (new information, character arrives, obstacle appears)
[Climax]    → Peak tension moment (confrontation, revelation, decision)
[Outcome]   → Scene-ending change (resolution or cliffhanger leading to next scene)
```

### SHORT mode: 3 events per scene
### CHAPTER mode: 5 events per scene

---

## 7. Scene Progression Metrics

### Every scene must have:
1. **Beginning** — location + character presence established
2. **Development** — interaction (action or dialogue)
3. **Change** — something is different at the end than at the start
4. **Outcome** — hooks into the next scene

### No scene is static.

---

## 8. Realizer Evaluation Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Dialogue Density | quoted dialogue words / total words | >15% |
| Event Density | distinct events / scene | >3 |
| Emotional Expression | behavior words / emotion label words | >5:1 |
| Causal Progression | causal connectors ("because", "so", "then") / sentences | >0.1 |
| Show-vs-Tell Ratio | concrete action verbs / abstract state verbs | >3:1 |
| Scene Change Magnitude | unique words between consecutive scenes | >30% |

---

## 9. Three Options Comparison

| Dimension | Option A: Improve CompRealizer | Option B: Hybrid (Events + LLM) | Option C: Full LLM |
|-----------|-------------------------------|--------------------------------|-------------------|
| **Complexity** | Medium — rewrite 5 methods | High — LLM integration + structured events | Very High — prompt engineering + fallback |
| **Quality ceiling** | Medium — constrained by word pools | High — LLM handles fluency, events handle structure | Highest |
| **Controllability** | High — every word is rule-governed | Medium-High — events constrain, LLM fills | Low — prompt-only |
| **Cost** | Zero (no API) | Medium (LLM calls per scene) | High (LLM for everything) |
| **Implementation effort** | 1-2 days | 4-5 days | 5-7 days |
| **Determinism** | Full | Partial (LLM variability) | Low |
| **Risk** | Prose may still feel mechanical | LLM latency, prompt brittleness | Hallucination, cost, latency |

### Recommendation: Option A (Improve CompositionalRealizer)

**Reasoning**: The audit shows subsystems produce meaningful influence (0.28-0.48 divergence). The bottleneck is not data availability but the Realizer's failure to transform that data into narrative. Improving the realizer is the highest-leverage path because:
1. All required data already exists in SceneBlueprint
2. No external dependencies needed
3. Full determinism preserved
4. Can be validated against the same 8 audit metrics
5. 1-2 day implementation vs 4-7 days for LLM options

---

## 10. Final Recommendation

### Exact Bottleneck
The CompositionalRealizer's `realize()` method produces simulation-log prose because it composes *descriptions of state* rather than *events with consequences*. Every method emits one static template sentence with no causal relationship between sentences.

### Exact Implementation Order
1. **Build DramaticEvent dataclass** and EventChain builder (event_sequencer module)
2. **Rewrite DialogueComposer** with quoted speech and intent-based templates
3. **Rewrite ActionSequencer** with concrete verbs and location-aware actions
4. **Rewrite EmotionRealizer** as behavioral expression (not labels)
5. **Build ShowNotTell mapper** that converts abstract states to concrete actions
6. **Rewrite OutputComposer** to assemble event chain into paragraphs
7. **Update CompositionalRealizer** to delegate to EventChain
8. **Re-run validation audit** to measure improvement

### Expected Gains
| Metric | Before | After (target) |
|--------|--------|----------------|
| Dialogue density | 0% | >15% |
| Simulation-log sentences | 8.7 avg | <1 avg |
| Emotional expression | 0.11/1.0 | >0.5/1.0 |
| Reader experience | 0.50/1.0 | >0.7/1.0 |
| Unique sentence start ratio | 0.69 | >0.85 |

### Risks
1. Word pool size — templates may still feel repetitive over many generations
2. Dialogue quality — templates produce grammatical speech but not great speech
3. If subsystems provide poor intentions/goals, Show-vs-Tell has nothing to show
4. Solution: Fall back to Option B (Hybrid) when evaluation metrics plateau
