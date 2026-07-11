# SCRIPTY Narrative Quality Execution Plan

> Ranked execution plan to measurably improve narrative quality across Realizer, Memory, Character, Retrieval, and Evaluation subsystems.
> Generated: 2026-06-09 | Base: 201 passing tests

---

## Tracking Table

| Phase | Assigned To | Status | Before | After | Δ | Complexity |
|-------|-------------|--------|--------|-------|---|------------|
| 1a | builder-hwse | ⬜ Pending | grammar errors in 30%+ action sentences | 0 grammar errors | — | 1 |
| 1b | builder-hwse | ⬜ Pending | dialogue tags: 5 generic pools | character-specific tag pools per voice | — | 2 |
| 1c | builder-hwse | ⬜ Pending | show-vs-tell: <1:1 ratio | show-vs-tell: >3:1 | — | 3 |
| 1d | builder-hwse | ⬜ Pending | action verbs: shared pools | action verbs: character-specific pools | — | 2 |
| 1e | builder-hwse | ⬜ Pending | body language: generic per emotion | body language: OCEAN×emotion selection | — | 2 |
| 2a | builder-memory | ⬜ Pending | Interpretation: 0% prose influence | Interpretation: direct entry in SceneBlueprint | — | 3 |
| 2b | builder-memory | ⬜ Pending | Semantic facts: generic pool only | Semantic facts: dedicated "realized that" prose | — | 2 |
| 2c | builder-hwse | ⬜ Pending | Callback pronoun mismatch | callback uses correct character reference | — | 1 |
| 2d | builder-memory | ⬜ Pending | RAG: 1/8 depth | RAG: injected into beliefs + callback | — | 2 |
| 3a | builder-character | ⬜ Pending | voice formality filters only dialogue lines | voice formality/tendency → sentence structure | — | 2 |
| 3b | builder-character | ⬜ Pending | BehavioralDrift → only dialogue tags | BehavioralDrift → body language + action verbs | — | 2 |
| 3c | builder-character | ⬜ Pending | OCEAN→emotion_key thresholds only | OCEAN→body language pool subset selection | — | 1 |
| 3d | builder-character | ⬜ Pending | subtext: 30% chance appended | subtext: 60% chance, integrated into tag | — | 1 |
| 4a | builder-retrieval | ⬜ Pending | RAG: keyword substring | RAG: TF-IDF or all-MiniLM-L6-v2 dense | — | 3 |
| 4b | builder-retrieval | ⬜ Pending | top_k=3 | top_k=5 | — | 1 |
| 4c | builder-retrieval | ⬜ Pending | no diversity penalty | diversity penalty (0.3 threshold) | — | 1 |
| 5 | tester | ⬜ Pending | no before/after measurement | before/after report generated | — | 2 |

---

## Priority Ranking (1 = highest impact / lowest complexity)

### Priority 1: Realizer Upgrade
1a. **Fix belief injection grammar** — Single-line fix at `dramatic_realizer.py:804`. The "aware of {raw truncated text}" produces ungrammatical phrases like "aware of a tense moment from chapter 1 still haunted arjun". Change to use a grammatical wrapper function.

1b. **Character-specific dialogue tag pools** — Currently 5 generic tag pools (ANGRY/SAD/FEARFUL/CALM/DEFAULT). Add voice fingerprint formality/vocabulary-level filtering to select which pool subset each character draws from. Already partially done at line selection level but not at tag level.

1c. **Show-not-tell mapping** — Abstract emotional states ("he was angry") produce hardcoded body language. Add a function that generates concrete behavioral text from abstract state + personality + target relationship.

1d. **Intention→character-specific verb pools** — `_ACTION_VERBS` shared across all characters. Add per-character verb pool subsets based on traits (brave→forward verbs, deceptive→subtle verbs, cautious→indirect verbs).

1e. **OCEAN×emotion body language** — `_BODY_LANGUAGE` has 7 fixed emotion keys. Add trait dimension: characters with different OCEAN profiles select from different subsets of the pool (a proud character's "angry" is different from a fearful character's "angry").

### Priority 2: Memory-to-Prose Transformation
2a. **Wire Interpretation Memory into SceneBlueprint** — `InterpretationEngine` has 207 LOC, generates 12+ entries per story (confirmed active), but only boosts relevance scores. Add interpretation text as direct entries in `retrieved_memories` and inject into `_compose_character_action()` via `_compose_memory_callback()` or a dedicated `_compose_interpretation()` method.

2b. **Wire Semantic facts into dedicated prose insertion** — Semantic facts sit in the memory pool competing with episodic entries. Add a parallel insertion path in `_compose_character_action()` that uses semantic facts directly (e.g., "{name} had realized that {fact}").

2c. **Fix callback pronoun mismatch** — Line 1074 uses `bp.objective.characters_involved[0]` as pronoun target. When callback text references a different character, pronoun mismatch occurs. Fix by extracting the subject from callback memory text.

2d. **RAG → belief injection** — RAGBridge retrieves corpus entries but they only enter `_compose_memory_callback()` via the general pool. Add a dedicated insertion path where RAG entries are placed in `beliefs.discovered` or directly referenced in `_compose_character_action()` as contextual knowledge.

### Priority 3: Character Differentiation Visibility
3a. **Voice formality/rhythm → dialogue sentence structure** — VoiceFingerprint has `sentence_tendency` (short/varied/complex/fragmented) and `vocabulary_level`. Currently filters `_DIALOGUE_LINES` by length. Add sentence structure modifiers: short sentences get different punctuation, complex sentences get subclause markers, fragmented gets ellipses/dashes.

3b. **BehavioralDrift pattern → body language + action verbs** — Drift pattern (consistent/aggressive/cautious/erratic/desperate) only affects dialogue tags. Add to `_compose_character_action()`: desperation→erratic body language, aggression→forward verbs, caution→indirect verbs.

3c. **OCEAN traits → body language subset** — `_emotion_key()` already uses traits for pressure thresholds. Add trait-based filtering to `_BODY_LANGUAGE` selection so proud characters use different "angry" body language than anxious ones.

3d. **Relationship history → dialogue subtext visibility** — Subtext currently appended with 30% chance ("{name} was {subtext}"). Increase to 60% chance when relationship is non-NEUTRAL, and integrate subtext into tag when possible (e.g., "said... warily" for RIVAL subtext).

### Priority 4: Retrieval Quality
4a. **RAGBridge: keyword → TF-IDF** — Currently uses `any(kw in text.lower() for kw in keywords)` substring matching. Replace with TF-IDF vectorizer (existing implementation in `backend/research/rag_pipeline.py`) or reuse `all-MiniLM-L6-v2` embeddings from `data_pipeline/output/faiss_index`.

4b. **top_K: 3 → 5** — Pipeline line 110, 116 hardcode `top_k=3`. Change to 5 for richer memory pool (already in `MemoryQuery` type default of `top_k=5`).

4c. **Diversity penalty** — Add diversity check: after retrieval, if any two entries have >0.8 cosine similarity (or 80%+ word overlap), drop the lower-ranked duplicate.

### Priority 5: Benchmark Validation
5. **Before/after measurement** — Run automated judge on 10 stories before any changes, then after all phases. Measure: dialogue density, show-vs-tell ratio, unique sentence starts, emotional expression, repetition rate, coherence score.

---

## Phase 1a: Fix Belief Injection Grammar
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** Grammar errors in ~30%+ action sentences containing "aware of" prefix from callback/belief text
**Target metric:** 0 ungrammatical "aware of" constructions
**Verification command:** Generate 3 SHORT stories and grep for "aware of"; inspect for subject-verb-object grammaticality
**Complexity:** 1 (single function edit)
**Impact point:** `dramatic_realizer.py:797-808` — `_compose_character_action()` belief injection block
**Acceptance criteria:** Every "aware of {X}" sentence reads as grammatical English where X is a noun phrase, not a raw sentence fragment

### Implementation steps:
1. Add a helper function `_grammaticalize_discovery(raw_text: str, character_name: str) -> str` that extracts the subject from raw text and converts it to a proper NP (e.g., truncates at the verb, wraps in "what happened", or substitutes "the event" when uncorrectable)
2. Replace lines 797-808 with call to this helper
3. Test: `python3 -c "from backend.v2.dramatic_realizer import _grammaticalize_discovery; print(_grammaticalize_discovery('A tense moment from chapter 1 still haunted Arjun', 'Arjun'))"` → outputs "what happened during the tense moment from chapter 1" or similar grammatical form

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.engine import StoryEngineV2
import asyncio
from backend.v2.types import GenerationRequest, StoryMode
req = GenerationRequest(location='Mumbai', year=1885, story_mode=StoryMode.SHORT, chapter_count=1)
e = StoryEngineV2()
result = asyncio.run(e.generate(req))
import re
matches = re.findall(r'aware of [^.]*\.', result.story_text)
for m in matches:
    assert m.endswith('.'), f'Bad grammar: {m}'
    words = m.split()
    assert len(words) > 3, f'Too short: {m}'
print(f'OK: {len(matches)} awareness sentences grammatical')
"`

---

## Phase 1b: Character-Specific Dialogue Tag Pools
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** 5 generic tag pools (ANGRY, SAD, FEARFUL, CALM, DEFAULT) — 31 tags total — all characters draw from same pools
**Target metric:** Each character's dialogue tags include at least 3 character-specific verbs from voice fingerprint mapping
**Verification command:** Generate story with 2+ characters, count unique tags per character
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:563-575` (tag pool definitions) + `dramatic_realizer.py:1009-1055` (`_build_dialogue_tag()`)
**Acceptance criteria:** Two characters with different voice fingerprints show <50% overlap in used dialogue tags over 3 stories

### Implementation steps:
1. Add `_TRAIT_DIALOGUE_TAGS: dict[str, list[str]]` — character trait→preferred tags (brave→{"growled","vowed","stated"}, deceptive→{"lied","fibbed","deflected"}, pious→{"intoned","blessed","prayed"})
2. In `_build_dialogue_tag()`, after drift/relationship check, apply a character-specific preference: pick from the trait-tagged pool with 40% probability when personality tag exists
3. Fallback to existing pools when no trait match

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.character_voice import VoiceFingerprintBuilder
from backend.v2.types import CharacterRecord
builder = VoiceFingerprintBuilder()
arjun = CharacterRecord(name='Arjun', role='protagonist', traits=['brave','curious'], goals=['uncover the truth'])
maya = CharacterRecord(name='Maya', role='antagonist', traits=['deceptive','cunning'], goals=['protect the secret'])
fp1 = builder.build(arjun)
fp2 = builder.build(maya)
print(f'Arjun formality={fp1.formality:.2f} tendency={fp1.sentence_tendency}')
print(f'Maya formality={fp2.formality:.2f} tendency={fp2.sentence_tendency}')
assert fp1.formality != fp2.formality or fp1.sentence_tendency != fp2.sentence_tendency, 'Fingerprints should differ'
"`

---

## Phase 1c: Show-Not-Tell Mapping
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** Emotional expression 0.11/1.0; show-vs-tell ratio <1:1
**Target metric:** Emotional expression >0.5/1.0; show-vs-tell ratio >3:1
**Verification command:** `python3 backend/v2/validation_audit.py --metric show_vs_tell`
**Complexity:** 3
**Impact point:** `dramatic_realizer.py:770-778` (`_emotion_key()`) + new method `_behavioral_expression()`
**Acceptance criteria:** Audit report shows emotional expression score >0.5 and show-vs-tell ratio >3:1 across 10 generated stories

### Implementation steps:
1. Create `_SHOW_VS_TELL: dict[str, dict[str, list[str]]]` mapping (emotion_key, relation_kind/target_trait) → concrete behavioral phrases. E.g., `"angry"` + `"proud"` → `["drew himself up to his full height", "his voice dropped to a dangerous quiet"]` vs `"angry"` + `"anxious"` → `["her fingers dug into her palms", "she couldn't stop shaking"]`
2. Create `_behavioral_expression(agent, target, pressure, traits) -> str` that selects from the show-vs-tell map and returns concrete action text instead of the body language + verb_phrase composition
3. Call `_behavioral_expression()` from `_compose_character_action()` to replace the abstract state → body language path when show-vs-tell map has entries
4. Keep `_BODY_LANGUAGE` as fallback when no concrete map entry exists

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: Generate 3 SHORT stories, count concrete behavioral verbs (clench, strike, reach, turn, step, grasp) vs abstract state verbs (is, was, felt, seemed). Ratio should be >3:1.

---

## Phase 1d: Character-Specific Action Verb Pools
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** All characters share same `_ACTION_VERBS` pools
**Target metric:** Each character has distinct verb preference from their trait pool
**Verification command:** Generate story with 2+ characters, count verb overlap between characters
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:779-794` (`_ACTION_VERBS`) + `dramatic_realizer.py:877-878` (verb_phrase selection)
**Acceptance criteria:** Two characters with different traits show <60% verb phrase overlap over 3 stories

### Implementation steps:
1. Add `_TRAIT_ACTION_VERBS: dict[str, dict[str, list[str]]]` — trait→action_key→verbs. E.g., brave→confront: `["stepped toward fearlessly", "stood his ground before", "met head-on"]`; cunning→confront: `["circled", "approached from an angle", "positioned himself between"]`
2. In `_compose_character_action()` line 877, after getting `action_key`, check if character traits have preferred verbs for this action key
3. If trait-specific verbs exist, use them with 50% probability; fallback to shared `_ACTION_VERBS`
4. Ensure `_ACTION_VERBS` still works for characters without trait matches (all characters have at least one trait)

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.dramatic_realizer import _ACTION_VERBS
print(f'Total verb pools: {len(_ACTION_VERBS)}')
print(f'Confront verbs: {_ACTION_VERBS[\"confront\"]}')
# Check trait_verbs exist if added
try:
    from backend.v2.dramatic_realizer import _TRAIT_ACTION_VERBS
    assert len(_TRAIT_ACTION_VERBS) > 0, 'Trait verb pools must exist'
    print(f'Trait verb pools: YES, keys={list(_TRAIT_ACTION_VERBS.keys())}')
except ImportError:
    print('Trait verb pools: NOT YET IMPLEMENTED')
"`

---

## Phase 1e: OCEAN×Emotion Body Language
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** `_BODY_LANGUAGE` has 7 flat emotion keys (angry, fearful, sad, anxious, desperate, calm, neutral) — no trait modulation
**Target metric:** Body language selected from character-trait-filtered subset within each emotion key
**Verification command:** Generate 2 characters with different traits in same emotional state; body language should differ observably
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:755-771` (body language dict) + `dramatic_realizer.py:884-885` (selection)
**Acceptance criteria:** Across 5 generated stories, two characters with different trait sets in similar emotional states (pressure ±0.15) use different body language phrases >60% of the time

### Implementation steps:
1. Extend `_BODY_LANGUAGE` entries to include trait tags (optional suffix list indicating compatible traits). E.g., `"His fists clenched at his sides."` gets traits: `["angry","bitter","brave"]`; `"A vein pulsed in his neck."` gets traits: `["proud","angry","arrogant"]`
2. Add trait-based filtering in selection: when picking body language, prefer entries whose traits overlap with the character's traits
3. Fallback to full pool when no character-trait-matched entries exist for the emotion key

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.dramatic_realizer import _BODY_LANGUAGE
print(f'Body language pools: {len(_BODY_LANGUAGE)} keys')
for k, v in _BODY_LANGUAGE.items():
    print(f'  {k}: {len(v)} items')
# Check trait-annotated entries
total_items = sum(len(v) for v in _BODY_LANGUAGE.values())
print(f'Total body language items: {total_items}')
"`

---

## Phase 2a: Wire Interpretation Memory into Prose
**Target subsystem:** Memory
**Assigned agent type:** builder-memory
**Current metric:** Interpretation: 0% prose influence (L3-L7 all ❌ Dead)
**Target metric:** Interpretation entries directly appear in scene text via callback or dedicated insertion
**Verification command:** Generate 3 SHORT stories, check for interpretation-derived text ("saw it as", "interpreted it as", "to them it seemed")
**Complexity:** 3
**Impact point:** `memory_system.py:203-211` (interpretation query) + `dramatic_realizer.py:1062-1090` (or new method `_compose_interpretation()`) + `pipeline.py:155-162` (blueprint build)
**Acceptance criteria:** Over 3 SHORT stories, at least 1 scene contains text directly traceable to an InterpretationEntry (not just boosted relevance)

### Implementation steps:
1. In `MemorySystem.retrieve()`, after relevance boosting (line 203-211), add interpretation text as separate MemoryEntries with `source="interpretation"` and a unique character context marker
2. In `SceneBlueprint`, add an `interpretations: list[InterpretationEntry]` field
3. In `pipeline.py` line 155-162, populate `interpretations` from `memory.query_interpretations()` for each agent
4. In `DramaticRealizer._compose_character_action()` or as a new COMPLICATION event, add interpretation text: `"{char} saw it differently — {interpretation_text}"` with 30% probability
5. Update `SceneBlueprint` dataclass in `types.py` to include `interpretations` field

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201+ tests)
Then verify: `python3 -c "
from backend.v2.memory_system import MemorySystem
m = MemorySystem()
entry = m.interpret_event('Arjun stepped onto the platform', 'Arjun', ['curious','brave'])
print(f'Interpretation: {entry.interpretation_text}')
print(f'Confidence: {entry.confidence}')
assert len(entry.interpretation_text) > 20, 'Should produce meaningful interpretation'
"`

---

## Phase 2b: Wire Semantic Facts into Dedicated Prose
**Target subsystem:** Memory
**Assigned agent type:** builder-memory
**Current metric:** Semantic facts: 2.5/8 depth — facts sit in pool with no dedicated insertion (L4-L6 ❌ Dead)
**Target metric:** Semantic facts directly inserted in prose via "had realized that" or "knew that" construction
**Verification command:** Generate story, check for "had realized that", "knew that", "understood that" phrases containing semantic fact content
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:797-808` (belief block) + `state_update.py:122-137` (record_fact)
**Acceptance criteria:** Over 3 SHORT stories, at least 2 scenes contain text directly from SemanticStore entries

### Implementation steps:
1. In `state_update.py` line 122-137, after recording facts, also inject factual summaries into `beliefs.discovered` (format: `"{name} realized that {fact}"`)
2. In `_compose_character_action()` line 797-808, add a check for semantic-type entries in `retrieved_memories` and generate: `"{name} knew that {fact_text[:50]}"` — appended after the main action description
3. Ensure semantic facts in `retrieved_memories` get `relevance_score=1.0` so they are strongly weighted in `_compose_memory_callback()` selection

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.memory_system import MemorySystem
m = MemorySystem()
m.record_fact('Arjun realized the platform was dangerous', 1, 1, ['Arjun'])
facts = m.semantic.query('Arjun')
print(f'Semantic facts: {len(facts)}')
assert len(facts) > 0, 'Facts should be retrievable'
"`

---

## Phase 2c: Fix Callback Pronoun Mismatch
**Target subsystem:** Realizer
**Assigned agent type:** builder-hwse
**Current metric:** Callback `_compose_memory_callback()` at line 1074 uses `bp.objective.characters_involved[0]` regardless of who the memory text references
**Target metric:** Callback uses the correct character name extracted from memory text
**Verification command:** Generate story with callback-injected memory, check pronoun-character agreement
**Complexity:** 1
**Impact point:** `dramatic_realizer.py:1062-1090` (`_compose_memory_callback()`)
**Acceptance criteria:** No instance of "{character} had not forgotten" where the character referenced in the memory text is different from the pronoun target

### Implementation steps:
1. Extract character names from `mem.text` by checking which scene-involved characters appear in the text (using `mem.characters` field or substring match against `bp.objective.characters_involved`)
2. Use the extracted character as the pronoun target instead of `bp.objective.characters_involved[0]`
3. Fallback to `characters_involved[0]` when no match found

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
import re
# Pattern to detect pronoun mismatch in callback templates: 'A memory surfaced — ... X had not forgotten'
# If the memory text says 'haunted Arjun' but the template says 'Maya had not forgotten', that's a mismatch
test_template = 'A memory surfaced — A tense moment from chapter 1 still haunted Arjun. Maya had not forgotten.'
# Should be 'Arjun had not forgotten'
matches = re.findall(r'haunted (\w+)\. (\w+) had not forgotten', test_template)
if matches:
    for subject, pronoun in matches:
        assert subject == pronoun, f'PRONOUN MISMATCH: memory references {subject} but template uses {pronoun}'
        print(f'OK: {subject} == {pronoun}')
"`

---

## Phase 2d: RAG → Belief Injection
**Target subsystem:** Memory
**Assigned agent type:** builder-memory
**Current metric:** RAG: 1/8 depth — only enters memory pool, no dedicated prose insertion
**Target metric:** RAG entries injected into beliefs or as contextual reference in action text
**Verification command:** Generate story with RAG enabled, check for corpus-derived knowledge in scene text
**Complexity:** 2
**Impact point:** `memory_system.py:213-219` (RAG retrieval) + `pipeline.py:110-138` (memory retrieval flow)
**Acceptance criteria:** Over 3 SHORT stories with RAG enabled, at least 1 scene contains text referencing corpus-derived information

### Implementation steps:
1. In `pipeline.py` memory retrieval section (line 110+), after RAG entries are merged, inject them into `beliefs_for(focus_character).discovered` as contextual knowledge
2. Mark RAG entries with `source="rag_corpus"` and a `relevance_score=0.6` so they appear in callback selection
3. In `_compose_character_action()`, add a check for RAG entries in `retrieved_memories` to generate contextual reference: `"{name} remembered something important — {rag_text[:80]}"`

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.rag_bridge import RAGBridge
rag = RAGBridge()
loaded = rag.load()
print(f'RAG loaded: {loaded}')
if loaded:
    print(f'Corpus size: {len(rag._corpus)}')
    from backend.v2.types import MemoryQuery
    q = MemoryQuery('Arjun', 'truth', top_k=3)
    results = rag.retrieve(q)
    print(f'RAG results for \"truth\": {len(results)}')
"`

---

## Phase 3a: Voice Formality/Rhythm → Dialogue Sentence Structure
**Target subsystem:** Character
**Assigned agent type:** builder-character
**Current metric:** VoiceFingerprint formality (0.0-1.0), vocabulary_level, sentence_tendency, speech_rhythm only filter `_DIALOGUE_LINES` by length
**Target metric:** Voice properties produce structurally different dialogue sentences (formal characters use longer/grammatically complete sentences; terse characters use fragments/commands)
**Verification command:** Generate 2 characters with opposite formality (0.8 vs 0.2), compare their dialogue sentence structures
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:935-966` (voice-fingerprint line filtering block) + `dramatic_realizer.py:976-983` (dialogue selection)
**Acceptance criteria:** High-formality character's dialogue contains clauses, longer words, fewer contractions vs low-formality character across 3 stories

### Implementation steps:
1. Add a `_apply_voice_structure(voice_fp, dialogue_text) -> str` method that transforms dialogue text based on voice fingerprint:
   - `formality > 0.7`: Expand contractions ("don't"→"do not"), prefer longer wording ("stop"→"cease")
   - `formality < 0.3`: Ensure contractions present, add colloquial markers
   - `sentence_tendency == "fragmented"`: Break into short segments with ellipses
   - `sentence_tendency == "complex"`: Add subclause markers ("though", "however", "nevertheless")
   - `speech_rhythm == "terse"`: Reduce by removing filler words
2. Apply this transformation in `_compose_dialogue_line()` after line selection (line 983) but before template application (line 1010-1012)

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.character_voice import VoiceFingerprintBuilder, VoiceFingerprint
from backend.v2.types import CharacterRecord
builder = VoiceFingerprintBuilder()
formal = builder.build(CharacterRecord(name='X', role='sage', traits=['wise','pious'], goals=['guide']))
informal = builder.build(CharacterRecord(name='Y', role='trickster', traits=['rude','brash'], goals=['trick']))
print(f'Formal formality={formal.formality:.2f} rhythm={formal.speech_rhythm} vocab={formal.vocabulary_level}')
print(f'Informal formality={informal.formality:.2f} rhythm={informal.speech_rhythm} vocab={informal.vocabulary_level}')
assert formal.formality > 0.6 or informal.formality < 0.4, 'Should show formality contrast'
"`

---

## Phase 3b: BehavioralDrift → Body Language + Action Verbs
**Target subsystem:** Character
**Assigned agent type:** builder-character
**Current metric:** Drift decision_pattern affects only dialogue tags (and intention selection in character_agent.py)
**Target metric:** Drift pattern visibly changes body language and action verb choices in realizer output
**Verification command:** Generate 2+ scenes with character's drift changing from "cautious" to "aggressive"; body language and verbs should change observably
**Complexity:** 2
**Impact point:** `dramatic_realizer.py:856-864` (drift_pattern in _compose_character_action) + `dramatic_realizer.py:877-878` (verb selection) + `dramatic_realizer.py:884-885` (body language selection)
**Acceptance criteria:** A character's body language and verb choices in a high-pressure scene (drift=desperate) differ from low-pressure (drift=consistent) by >50% unique phrase usage

### Implementation steps:
1. In `_compose_character_action()`, pass `drift_pattern` to `_emotion_key()` or use it to modulate the body language selection directly
2. Add drift override: if `drift_pattern == "desperate"`, prefer `_BODY_LANGUAGE["desperate"]` entries even when pressure < 0.8
3. If `drift_pattern == "aggressive"`, prefer confront/attack action verbs when available
4. If `drift_pattern == "cautious"`, prefer observe/wait/negotiate verbs and anxious/neutral body language

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.character_drift import BehavioralDriftTracker
from backend.v2.types import CharacterRecord
tracker = BehavioralDriftTracker()
c = CharacterRecord(name='Test', role='protagonist', traits=['brave'], goals=['survive'])
tracker.register_character(c)
drift1 = tracker.compute_drift(c, 0.2)  # low pressure
drift2 = tracker.compute_drift(c, 0.75)  # high pressure
print(f'Low pressure: pattern={drift1.decision_pattern}')
print(f'High pressure: pattern={drift2.decision_pattern}')
assert drift1.decision_pattern != drift2.decision_pattern, 'Drift pattern should change with pressure'
"`

---

## Phase 3c: OCEAN Traits → Body Language Subsetting
**Target subsystem:** Character
**Assigned agent type:** builder-character
**Current metric:** `_emotion_key()` uses traits for pressure thresholds, but all characters with same emotion key get same body language
**Target metric:** Characters with same emotion key but different OCEAN profiles get different body language
**Verification command:** Two characters both at "angry" emotion key but with different traits produce different body language
**Complexity:** 1
**Impact point:** `dramatic_realizer.py:884-885` (body language selection via random.choice) + `dramatic_realizer.py:755-771` (body language trait tags)
**Acceptance criteria:** Across 10 scenes where two characters share the same emotion key, their body language differs >70% of the time

### Implementation steps:
1. Add trait tags to existing `_BODY_LANGUAGE` entries (already specified in Phase 1e)
2. In the selection line (884-885), change from `random.choice(_BODY_LANGUAGE[ekey])` to weighted selection: prefer entries whose trait tags match the character's traits (3x weight), fallback to uniform selection
3. This is a 3-line change in `_compose_character_action()`

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
# Verify trait-tagged body language entries exist (from Phase 1e)
from backend.v2.dramatic_realizer import _BODY_LANGUAGE
# Check if entries have trait metadata
sample = _BODY_LANGUAGE.get('angry', [])
print(f'Angry pool: {len(sample)} items')
"`

---

## Phase 3d: Relationship History → Dialogue Subtext Visibility
**Target subsystem:** Character
**Assigned agent type:** builder-character
**Current metric:** Subtext appended with 30% probability as "{name} was {subtext}" sentence fragment
**Target metric:** Subtext integrated into dialogue tag with 60% probability for non-NEUTRAL relationships
**Verification command:** Generate 2 characters with ENEMY relationship, check dialogue lines for subtext integration
**Complexity:** 1
**Impact point:** `dramatic_realizer.py:1057-1059` (subtext append)
**Acceptance criteria:** In multi-character scenes with non-NEUTRAL relationships, >50% of dialogue lines show subtext integration

### Implementation steps:
1. Change line 1057 from `if subtext and random.random() < 0.3:` to `if subtext:`
2. For non-NEUTRAL relationships, use `random.random() < 0.6` threshold
3. For NEUTRAL, use `random.random() < 0.3` (unchanged)
4. Add subtext keyword to dialogue tag when possible: `"said... with hidden {subtext}"` format for relationship-congruent subtext

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: Generate 1 SHORT story with 2 characters in RIVAL relationship, count dialogue lines with subtext markers ("was actually", "with hidden", "hiding", "testing").

---

## Phase 4a: RAGBridge Upgrade to TF-IDF
**Target subsystem:** Retrieval
**Assigned agent type:** builder-retrieval
**Current metric:** `rag_bridge.py:34-52` — keyword substring matching (`any(kw in text.lower() for kw in keywords)`)
**Target metric:** TF-IDF or all-MiniLM-L6-v2 dense retrieval with cosine similarity scoring
**Verification command:** `python3 -c "from backend.v2.rag_bridge import RAGBridge; r=RAGBridge(); r.load(); print(r.retrieve(...))"`
**Complexity:** 3
**Impact point:** `rag_bridge.py:34-52` (retrieve method)
**Acceptance criteria:** RAG retrieval returns entries ranked by relevance score, not just keyword presence; top result has >0.5 cosine similarity to query

### Implementation steps:
1. Add TF-IDF vectorizer (sklearn) in `RAGBridge.__init__()`: fit on `self._corpus` texts during `load()`
2. Rewrite `retrieve()`: transform query with the fitted vectorizer, compute cosine similarity, sort by score, return top-K
3. Ensure backward compatibility: if sklearn is not available or vectorization fails, fall back to keyword substring matching
4. (Optional) Use existing all-MiniLM-L6-v2 from `backend/research/embedding_encoder.py` for dense retrieval when available

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.rag_bridge import RAGBridge
from backend.v2.types import MemoryQuery
rag = RAGBridge()
rag.load()
q = MemoryQuery('Arjun', 'hidden secret revealed', top_k=3)
results = rag.retrieve(q)
print(f'Results: {len(results)}')
for r in results:
    print(f'  score={r.relevance_score:.3f} text={r.text[:60]}...')
assert len(results) > 0, 'Should return at least 1 result'
"`

---

## Phase 4b: Increase top-K from 3 to 5
**Target subsystem:** Retrieval
**Assigned agent type:** builder-retrieval
**Current metric:** `pipeline.py:110, 116` — hardcoded `top_k=3`
**Target metric:** `top_k=5` for richer memory pool
**Verification command:** `grep "top_k" backend/v2/pipeline.py`
**Complexity:** 1
**Impact point:** `pipeline.py:110, 116` (two lines)
**Acceptance criteria:** Pipeline passes `top_k=5` to MemoryQuery

### Implementation steps:
1. Change line 110: `top_k=3` → `top_k=5`
2. Change line 116: `top_k=3` → `top_k=5`

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `grep -n "top_k=3" backend/v2/pipeline.py` should return no matches

---

## Phase 4c: Add Diversity Penalty to Retrieval
**Target subsystem:** Retrieval
**Assigned agent type:** builder-retrieval
**Current metric:** No diversity check — same memory can be retrieved twice or near-identical entries selected
**Target metric:** Retrieved entries have minimum diversity threshold: no two entries with >80% word overlap
**Verification command:** Generate story with repetitive context, check retrieved memory overlap
**Complexity:** 1
**Impact point:** `memory_system.py:225-231` (final return in retrieve method)
**Acceptance criteria:** No two entries in retrieved results share >80% word-level overlap

### Implementation steps:
1. Add a diversity filter at `memory_system.py:225-231`: after collecting results, compute word-set Jaccard similarity between each pair
2. If any pair's Jaccard similarity >0.8, drop the lower-ranked entry and pull the next candidate (if any)
3. Ensure this doesn't reduce results below 1 entry

### Quality gate:
After implementation, run: `python3 -m pytest backend/v2/ -q` (must pass 201 tests)
Then verify: `python3 -c "
from backend.v2.memory_system import MemorySystem
m = MemorySystem()
m.record_event('Arjun walked through the dark tunnel', 1, 1, ['Arjun'], 0.8)
m.record_event('Arjun walked through the dark tunnel carefully', 1, 1, ['Arjun'], 0.7)
m.record_event('Maya discovered a hidden letter', 1, 1, ['Maya'], 0.9)
from backend.v2.types import MemoryQuery
results = m.retrieve(MemoryQuery('Arjun', 'walking', top_k=5))
print(f'Retrieved: {len(results)} entries')
for r in results:
    print(f'  score={r.relevance_score} text={r.text[:50]}')
# Should not have both near-identical first two entries
texts = [r.text[:40] for r in results]
assert len(set(texts)) >= len(texts) - 1, 'Should not have duplicate entries'
"`

---

## Phase 5: Benchmark Validation
**Target subsystem:** Evaluation
**Assigned agent type:** tester
**Current metric:** No automated before/after measurement pipeline for narrative quality metrics
**Target metric:** Before/after comparison report with all 6 key metrics
**Verification command:** `python3 backend/v2/narrative_quality_plan.py --run-benchmark`
**Complexity:** 2
**Impact point:** New file `backend/v2/narrative_quality_benchmark.py`
**Acceptance criteria:** Report generated at `backend/v2/narrative_quality_report.md` with before/after/Δ columns for all 6 metrics

### Implementation steps:
1. Create `backend/v2/narrative_quality_benchmark.py` with these functions:
   - `generate_stories(count=10, seed=42)` — generates 10 SHORT stories with fixed seed
   - `measure_dialogue_density(stories)` — quoted words / total words
   - `measure_show_vs_tell(stories)` — concrete action verbs / abstract state verbs
   - `measure_unique_sentence_starts(stories)` — distinct first 3 words / total sentences
   - `measure_emotional_expression(stories)` — emotional behavior words / total emotional words
   - `measure_repetition_rate(stories)` — repeated bigrams / total bigrams
   - `measure_coherence(stories)` — uses existing coherence scorer from backend/research/
2. Run benchmark before any changes: `python3 -c "from backend.v2.narrative_quality_benchmark import *; run_benchmark('before')"`
3. Run benchmark after Phase 1-4: `python3 -c "from backend.v2.narrative_quality_benchmark import *; run_benchmark('after')"`
4. Generate comparison report: `python3 -c "from backend.v2.narrative_quality_benchmark import *; generate_report('before.json', 'after.json')"`

### Quality gate:
No test modification needed — this is a measurement-only phase.
Verify: `ls -la backend/v2/narrative_quality_report*.md` shows both before/after reports.

---

## Plan Aggregation Summary

```
Phase 1a: ✂️ 1 file, ~5 lines   Fix belief grammar
Phase 1b: ✂️ 1 file, ~30 lines  Character-specific dialogue tags
Phase 1c: ✂️ 1 file, ~60 lines  Show-not-tell mapping
Phase 1d: ✂️ 1 file, ~25 lines  Character-specific verb pools
Phase 1e: ✂️ 1 file, ~15 lines  OCEAN×emotion body language
Phase 2a: ✂️ 3 files, ~40 lines Wire Interpretation→SceneBlueprint
Phase 2b: ✂️ 2 files, ~15 lines Wire Semantic→"realized that" prose
Phase 2c: ✂️ 1 file,  ~8 lines  Fix callback pronoun mismatch
Phase 2d: ✂️ 2 files, ~10 lines RAG→belief injection
Phase 3a: ✂️ 1 file, ~40 lines  Voice formality→sentence structure
Phase 3b: ✂️ 1 file, ~20 lines  Drift→body language + verbs
Phase 3c: ✂️ 1 file,  ~5 lines  OCEAN→body language subset
Phase 3d: ✂️ 1 file,  ~5 lines  Higher subtext probability
Phase 4a: ✂️ 1 file, ~50 lines  RAGBridge→TF-IDF
Phase 4b: ✂️ 1 file,  ~2 lines  top_k 3→5
Phase 4c: ✂️ 1 file, ~15 lines  Diversity penalty
Phase 5:  ✂️ 1 file, ~120 lines Benchmark script + report

Total: ~465 lines changed across 8 files
Total new: ~120 lines (benchmark script)
Predicted test pass rate: 201+ (all existing + new benchmark tests)
```

---

## Execution Order Requirements

```
Phase 1a ──► Phase 1c ──► Phase 1e
  │                         │
  ├──► Phase 1b ───────────┤
  ├──► Phase 1d ───────────┤
  │                         │
  ▼                         ▼
Phase 2c ──► Phase 2a ──► Phase 2b ──► Phase 2d
                                         │
                                         ▼
Phase 3a ──► Phase 3b ──► Phase 3c ──► Phase 3d
                                         │
                                         ▼
Phase 4b ──► Phase 4c ──► Phase 4a
                              │
                              ▼
                          Phase 5
```

**Rationale:**
- Phase 1 changes are independent, can be done in parallel
- Phase 2 depends on 1a (grammar fix) because interpretation/semantic injection uses the same belief text pipeline
- Phase 3 depends on 1b/1d/1e (character differentiation requires character-specific pools to exist)
- Phase 4 is fully independent of 1-3
- Phase 5 must run last to capture all changes

---

## Rollback Plan

Each phase should be implemented on a separate branch or as a single commit per phase. If any phase causes test failures:
1. Revert the phase commit: `git revert HEAD`
2. Document the failure in `project_docs/SCRIPTY_AUDIT_HISTORY.md`
3. Move to next phase — do not block the pipeline

**Phase-specific rollback risk:**
| Phase | Risk | Mitigation |
|-------|------|------------|
| 1a | Very low — single expression change | Test generates scenes and checks grammar |
| 1b | Low — adds data, doesn't remove | Old pools still work as fallback |
| 1c | Low-Medium — new code path | Old path preserved as fallback |
| 2a | Medium — changes SceneBlueprint type | Must update all callers |
| 4a | Medium — new dependency (sklearn) | Fallback to keyword matching |
| 5 | None — measurement only | No production code change |
