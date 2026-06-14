from typing import List, Optional, Dict, Any
import logging
import time
from pathlib import Path

from data_pipeline.parsers.base_parser import ParsedDocument
from data_pipeline.schema.fragment import (
    NarrativeFragment, CharacterMemoryFragment,
    ForeshadowingLink, SceneBlueprint,
)
from data_pipeline.config import DEFAULT_PIPELINE_CONFIG, PASSES

from data_pipeline.passes.pass1_structural import StructuralParsingPass
from data_pipeline.passes.pass2_extraction import NarrativeFragmentExtractionPass
from data_pipeline.passes.pass3_characters import CharacterExtractionPass
from data_pipeline.passes.pass4_relationships import RelationshipExtractionPass
from data_pipeline.passes.pass5_emotions import EmotionExtractionPass
from data_pipeline.passes.pass6_conflicts import ConflictExtractionPass
from data_pipeline.passes.pass7_narrative_devices import NarrativeDeviceExtractionPass
from data_pipeline.passes.pass8_worldbuilding import WorldbuildingExtractionPass
from data_pipeline.passes.pass9_scene_patterns import ScenePatternExtractionPass
from data_pipeline.passes.pass10_genre_patterns import GenrePatternExtractionPass

from data_pipeline.quality.quality_scorer import QualityScorer
from data_pipeline.quality.deduplicator import Deduplicator

from data_pipeline.analysis.character_memory import CharacterMemoryExtractor
from data_pipeline.analysis.foreshadowing import ForeshadowingExtractor
from data_pipeline.analysis.scene_patterns import ScenePatternExtractor

from data_pipeline.rag.embedding_builder import EmbeddingBuilder
from data_pipeline.rag.index_builder import IndexBuilder
from data_pipeline.rag.corpus_builder import CorpusBuilder

from data_pipeline.storage.fragment_store import FragmentStore
from data_pipeline.storage.jsonl_store import JsonlStore, JsonStore
from data_pipeline.storage.faiss_index import FaissIndexBuilder

from data_pipeline.reporting.reporter import Reporter


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**DEFAULT_PIPELINE_CONFIG, **(config or {})}
        self._ensure_dirs()

        self.parser = StructuralParsingPass()
        self.extractor = NarrativeFragmentExtractionPass()
        self.char_pass = CharacterExtractionPass()
        self.rel_pass = RelationshipExtractionPass()
        self.emotion_pass = EmotionExtractionPass()
        self.conflict_pass = ConflictExtractionPass()
        self.device_pass = NarrativeDeviceExtractionPass()
        self.wb_pass = WorldbuildingExtractionPass()
        self.scene_pass = ScenePatternExtractionPass()
        self.genre_pass = GenrePatternExtractionPass()
        self.quality_scorer = QualityScorer()
        self.deduplicator = Deduplicator()
        self.char_mem = CharacterMemoryExtractor()
        self.foreshadow = ForeshadowingExtractor()
        self.scene_patterns = ScenePatternExtractor()
        self.embedder = EmbeddingBuilder()
        self.index_builder = IndexBuilder()
        self.corpus_builder = CorpusBuilder()
        self.reporter = Reporter(self.config["report_dir"])
        self.fragment_store = FragmentStore(self.config["output_dir"])

        self.results = {
            "documents": [],
            "fragments": [],
            "character_memories": [],
            "foreshadowing_links": [],
            "scene_blueprints": [],
        }

    def _ensure_dirs(self):
        for key in ["output_dir", "cache_dir", "report_dir"]:
            Path(self.config[key]).mkdir(parents=True, exist_ok=True)

    def run(self, input_paths: Optional[List[str]] = None, input_dir: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("SCRIPTY Narrative Corpus Extraction Pipeline v1.0")
        logger.info("=" * 60)

        file_paths = input_paths or []
        if input_dir:
            file_paths.extend(self.parser.discover_files(input_dir))

        file_paths = list(set(file_paths))
        if not file_paths:
            logger.warning("No input files found. Use sample data for testing.")
            sample_path = self._generate_sample_data()
            if sample_path:
                file_paths = [sample_path]
            else:
                return {"status": "error", "message": "No input files"}

        logger.info(f"Processing {len(file_paths)} files")

        documents = self._run_pass("structural_parsing", self._parse_documents, file_paths)
        if not documents:
            return {"status": "error", "message": "No documents parsed"}

        raw_fragments = self._run_pass("fragment_extraction", self._extract_fragments, documents)
        if not raw_fragments:
            return {"status": "error", "message": "No fragments extracted"}

        self._run_pass("character_extraction", self._extract_characters, documents, raw_fragments)
        self._run_pass("relationship_extraction", self._extract_relationships, raw_fragments)
        self._run_pass("emotion_extraction", self._extract_emotions, raw_fragments)
        self._run_pass("conflict_extraction", self._extract_conflicts, raw_fragments)
        self._run_pass("narrative_device_extraction", self._extract_narrative_devices, raw_fragments)
        self._run_pass("worldbuilding_extraction", self._extract_worldbuilding, raw_fragments)
        self._run_pass("scene_pattern_extraction", self._extract_scene_patterns, raw_fragments)
        self._run_pass("genre_pattern_extraction", self._extract_genre_patterns, raw_fragments)

        scored = self._run_pass("quality_scoring", self._score_quality, raw_fragments)
        if not scored:
            return {"status": "error", "message": "No fragments passed quality filter"}

        deduped = self._run_pass("deduplication", self._deduplicate, scored)

        embedded = self._run_pass("embedding", self._embed_fragments, deduped)

        self._run_pass("rag_preparation", self._prepare_rag, embedded)

        self._run_pass("character_memory_extraction", self._extract_character_memories, documents, embedded)
        self._run_pass("foreshadowing_extraction", self._extract_foreshadowing, embedded)
        self._run_pass("scene_patterns_analysis", self._extract_scene_patterns_analysis, documents, embedded)

        self._run_pass("storage", self._store_results, embedded)

        reports = self._run_pass("reporting", self._generate_reports)

        elapsed = time.time() - start_time
        summary = self._build_summary(embedded, reports, elapsed)

        logger.info("=" * 60)
        logger.info(f"Pipeline complete: {len(embedded)} fragments in {elapsed:.1f}s")
        logger.info("=" * 60)

        return summary

    def _run_pass(self, name: str, func, *args, **kwargs):
        if hasattr(self, '_passes_enabled') and not hasattr(self, f'_pass_{name}_enabled'):
            return func(*args, **kwargs) if args else func(**kwargs)
        logger.info(f"[PASS] {name}")
        t = time.time()
        result = func(*args, **kwargs) if args else func(**kwargs)
        elapsed = time.time() - t
        logger.info(f"[PASS] {name} completed in {elapsed:.2f}s")
        return result

    def _parse_documents(self, file_paths: List[str]) -> List[ParsedDocument]:
        return self.parser.execute(file_paths)

    def _extract_fragments(self, documents: List[ParsedDocument]) -> List[NarrativeFragment]:
        return self.extractor.execute(documents)

    def _extract_characters(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]):
        return self.char_pass.execute(documents, fragments)

    def _extract_relationships(self, fragments: List[NarrativeFragment]):
        return self.rel_pass.execute(fragments)

    def _extract_emotions(self, fragments: List[NarrativeFragment]):
        return self.emotion_pass.execute(fragments)

    def _extract_conflicts(self, fragments: List[NarrativeFragment]):
        return self.conflict_pass.execute(fragments)

    def _extract_narrative_devices(self, fragments: List[NarrativeFragment]):
        return self.device_pass.execute(fragments)

    def _extract_worldbuilding(self, fragments: List[NarrativeFragment]):
        return self.wb_pass.execute(fragments)

    def _extract_scene_patterns(self, fragments: List[NarrativeFragment]):
        return self.scene_pass.execute(fragments)

    def _extract_genre_patterns(self, fragments: List[NarrativeFragment]):
        return self.genre_pass.execute(fragments)

    def _score_quality(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        return self.quality_scorer.score_fragments(fragments)

    def _deduplicate(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        return self.deduplicator.deduplicate(fragments)

    def _embed_fragments(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        return self.embedder.embed_fragments(fragments)

    def _prepare_rag(self, fragments: List[NarrativeFragment]):
        idx_path = self.config["faiss_index_path"]
        corpus_path = self.config["corpus_jsonl"]
        self.index_builder.build_and_save(fragments, idx_path)
        self.corpus_builder.build(fragments, corpus_path)

    def _extract_character_memories(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]):
        memories = self.char_mem.execute(documents, fragments)
        self.results["character_memories"] = memories
        store = JsonlStore.for_character_memories(self.config["character_memory_store"])
        store.append_batch(memories)
        logger.info(f"Saved {len(memories)} character memory fragments")

    def _extract_foreshadowing(self, fragments: List[NarrativeFragment]):
        links = self.foreshadow.execute(fragments)
        self.results["foreshadowing_links"] = links
        graph = [l.to_dict() for l in links]
        JsonStore.save_json(self.config["foreshadowing_graph"], graph)
        logger.info(f"Saved {len(links)} foreshadowing links")

    def _extract_scene_patterns_analysis(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]):
        blueprints = self.scene_patterns.execute(documents, fragments)
        self.results["scene_blueprints"] = blueprints
        store = JsonlStore.for_scene_blueprints(self.config["scene_blueprints"])
        store.append_batch(blueprints)
        logger.info(f"Saved {len(blueprints)} scene blueprints")

    def _store_results(self, fragments: List[NarrativeFragment]):
        self.fragment_store.save_fragments(fragments)
        self.results["fragments"] = fragments

    def _generate_reports(self) -> Dict[str, str]:
        return self.reporter.generate_all_reports(
            fragments=self.results["fragments"],
            foreshadowing_links=self.results["foreshadowing_links"],
            scene_blueprints=self.results["scene_blueprints"],
            character_memories=self.results["character_memories"],
        )

    def _build_summary(self, fragments: List[NarrativeFragment], reports: Dict[str, str], elapsed: float) -> Dict[str, Any]:
        stats = self.fragment_store.get_statistics()
        return {
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "total_fragments": len(fragments),
            "elite_fragments": sum(1 for f in fragments if f.is_elite()),
            "unique_books": stats.get("unique_books", 0),
            "categories_covered": len(stats.get("by_category", {})),
            "reports": reports,
            "output_dir": self.config["output_dir"],
            "config": {k: v for k, v in self.config.items() if not k.endswith("dir")},
        }

    def _generate_sample_data(self) -> Optional[str]:
        sample_dir = Path(self.config["cache_dir"]) / "samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        sample_path = sample_dir / "sample_novel.txt"
        if not sample_path.exists():
            sample_text = """Chapter 1: The Weight of Memory

The rain fell in relentless sheets across the ancient city of Veridia, each drop a tiny hammer against the weathered cobblestones, washing the last traces of blood into the gutters like forgotten sins. Captain Elena Marchetti pulled her crimson cloak tighter against the biting wind, her gloved fingers numb from the cold. She stood at the precipice of the Fountain District, watching the darkness swallow the narrow alleyways one by one, each swallowed shadow a secret the city refused to share. Something was wrong. She could feel it in her bones, the same visceral certainty she had felt before the Siege of Karthos, when the ground had trembled and the sky had turned the color of bruises.

"You're worried," said a voice behind her, soft and familiar as an old scar.

She turned to find Lieutenant Dravos emerging from the shadows like a ghost given form. His hand rested on his sword hilt, a gesture she had seen a thousand times before in a thousand different camps and courtyards. The rain had plastered his dark hair to his forehead, and his eyes held the weary wisdom of a man who had seen too much and forgotten too little.

"Not worried," she replied, her voice steady despite the churning in her chest. "Cautious. There is a difference, Lieutenant, and it has kept me alive long enough to learn it."

"The council wants answers by morning." Dravos stepped closer, his boots splashing in a puddle that reflected the distant torchlight like a shattered mirror. "They are afraid, Elena. I have seen them afraid before, but never like this. Never with this particular shade of terror in their eyes."

"The council can want all it likes." Her eyes narrowed to slits, the firelight catching the silver flecks in her irises. "I will not send good men and women to die on a guess, no matter how noble the guesswork sounds when dressed in velvet and seated on a throne."

Dravos nodded slowly, a sad smile touching his lips. "Three victims, all nobles, all on the night of the new moon. Lord Cassian, found in his study with his eyes wide open and his mouth frozen in a silent scream. Lady Mira, discovered in her garden surrounded by flowers that had bloomed overnight despite the winter frost. Master Aldric, the scholar, slumped over his desk as though he had simply fallen asleep mid-sentence. Tomorrow is the new moon."

"Then we have twelve hours." Elena's mind raced, years of training and instinct converging like rivers feeding a delta. She remembered the last time she had faced a conspiracy this deep, this ancient. It had cost her everything — her rank, her honor, her closest friend. The betrayal still burned like a brand seared into her soul, a scar that would never fade, a lesson she would never forget. The memory rose unbidden, sharp and painful as a shard of glass: Kaelen's face, the confusion in his eyes, the moment the blade had found its mark.

"Sir," Dravos said quietly, stepping closer still, his voice dropping to barely a whisper, "if I may speak freely without consequence."

"Always. You have earned that right, and more besides."

"You carry something heavy. Something that bends your shoulders when you think no one is watching. I see it in your eyes when the firelight catches them just so." He held her gaze, unflinching. "What happened at Karthos was not your fault. You know this, even if you cannot feel it."

She met his gaze, her expression hardening like cooling steel. "Some burdens are not meant to be shared, Dravos. They are meant to be carried until they either break us or we learn to stand beneath their weight."

"That is exactly when they need to be shared." He reached out, hesitated, and let his hand fall. "That is when the carrying becomes possible."

The wind howled through the narrow streets like a wounded animal, carrying the scent of rain and woodsmoke and something darker, something ancient and patient. Somewhere in the distance, the great bronze bell of the Grand Temple tolled midnight, each note a slow, resonant heartbeat in the darkness.

"Come," she said, turning to face the labyrinth of streets ahead. "We have work to do, and the night is not getting any younger."

They walked together into the velvet darkness of Veridia, two figures swallowed by a city that held more secrets than there were stars in the infinite sky above them.

---

Chapter 2: The Archive of Lost Knowledge

The Archive of Lost Knowledge lay buried beneath the Grand Temple, a vast labyrinth of shelves that stretched into eternal darkness like the ribs of some enormous, long-dead beast. Elena carried a lantern, its yellow flame a lonely star pushing back the shadows inch by painstaking inch. The air was thick with the smell of ancient paper, dried ink, and the peculiar mustiness of centuries pressed between leather covers.

"According to the records," Dravos said, reading from a leather-bound journal by the glow of his own small candle, "the first victim was Lord Cassian. He was found in his study at midnight, seated in his favorite chair, no signs of forced entry, no witnesses, no apparent cause of death. The physician called it heart failure, but the physician did not see the expression on his face."

"And what expression was that?"

"Rapture. As though he had seen something so beautiful, so terrible, that his soul had simply left his body to follow it."

Elena ran her fingers along a row of ancient texts, the leather spines cool and smooth beneath her touch. The titles were in languages she half-recognized, scripts that danced between the familiar and the alien. "There is a word for that in the old tongue of the Veridian priesthood. 'Animus Absentia.' The removal of the soul. It was considered the highest punishment for those who had seen forbidden truths."

"You believe in such things?" Dravos looked up from his journal, his expression unreadable in the flickering light.

"I believe in evidence, Lieutenant. And the evidence, cold and hard as it may be, suggests that something impossible has killed three people in a city that prides itself on its rationality." She paused, her fingers hovering over a book bound in what appeared to be silver thread, its spine glowing with a faint, internal luminescence. "And I believe that when you eliminate the impossible, whatever remains, however improbable, must be the truth."

A book caught her eye, bound in what appeared to be silver thread so fine it seemed woven from light itself. Its pages glowed faintly, pulsing with a rhythm that matched her heartbeat. She pulled it from the shelf.

"Elena." Dravos's voice was sharp, a blade cutting through the silence. "Do not."

"Why?" She turned the book over in her hands. It was warm to the touch.

"That book is bound with sirensilver. It is meant to contain something dangerous, something that should not be released into the world of men." His hand went to his sword. "Put it back. Please."

She opened it anyway, ignoring the warning in his voice and the cold dread spreading through her chest. The pages were blank, empty as a winter sky.

And then they were not.

Words appeared, written in fire, each letter burning itself into her retinas: THE TRUTH WILL BURN YOU.

Elena slammed the book shut, her heart pounding against her ribs like a caged bird. "We need to find whoever is behind this. Whoever is pulling the strings."

"No," said a new voice, soft and cold as the grave, emerging from the shadows between the towering shelves. "What you need to do is run."

A figure emerged, tall and cloaked, face hidden behind a silver mask that caught the lantern light and scattered it like water. The mask was expressionless, beautiful, terrible. "The Order of the Crimson Veil has watched you, Captain Elena Marchetti. We have watched you since the day you drew your first breath in this city. We know what you seek in these dusty halls. We know what you lost on the walls of Karthos. We know the name of the man who died in your arms, and we know the promise you made to him as the light left his eyes."

Elena's hand went to her sword, the blade singing as it left the scabbard. "Then you know I do not run. I have never run from anything in my life, and I will not start now, not for a ghost in a mask and not for an order that hides in shadows."

"A pity." The figure raised a hand, and the shadows seemed to deepen, to gather around the fingers like living things. "I had hoped you would make this interesting. I had hoped you would choose the wise path, the easy path. But I see now that the Mark of the Phoenix chose you for a reason, and that reason is that you are too stubborn to know when you are beaten."

The lantern went out.

Darkness fell like a hammer.

---

Chapter 3: The Mark Awakens

Elena woke to the smell of dust and old paper and something else, something metallic and sharp that she recognized from a hundred battlefields. She was lying on the cold stone floor of the Archive, her head throbbing with a pain that seemed to have its own heartbeat. The silver-bound book was gone. The lantern lay shattered beside her, its glass scattered like frozen tears.

"Dravos?" Her voice was a rasp, barely a whisper.

Silence answered her. Not the ordinary silence of an empty room, but the heavy, expectant silence of a held breath.

She scrambled to her feet, her sword already in her hand, the familiar weight of the hilt a comfort in the darkness. The shelves around her were scorched, blackened as if a fire had swept through and then vanished without consuming anything. The air tasted of ozone and ash.

"Impressive," said the voice from before, echoing from everywhere and nowhere at once. "Most people do not survive the Revelation. Most people's minds simply... shatter. Like glass dropped on stone."

Elena spun, trying to locate the source. The shadows moved in ways that shadows should not move, curling and uncurling like living things.

"Who are you?" she demanded, her voice steady despite the fear that coiled in her stomach like a serpent.

The masked figure stepped from behind a pillar, the silver book held loosely in one hand. "I am many things, Captain. I am the hand that moves in darkness. I am the voice that whispers in the ears of kings. I am the wall that stands between this world and the things that hunger for it from the spaces between stars."

"Pretty words." Elena shifted her stance, ready to strike. "They do not answer my question."

"No. They do not." The figure opened the book, and the pages caught fire, burning with a cold blue flame that cast no shadows. "The Crimson Veil has protected this city for three centuries. We have eliminated threats you cannot imagine — demons that wear the skins of men, dark mages who bargain with forces beyond comprehension, things that crawl between worlds on gossamer threads of nightmare. But a new danger rises. One even we cannot face alone."

"And you need me." It was not a question.

"We need the woman who survived the Siege of Karthos. The woman who faced the Shadow King and lived to tell the tale. The woman who carries within her chest the Mark of the Phoenix, the ancient sigil of the fire that burns away lies and reveals truth."

Elena's blood ran cold, colder than the rain that had soaked her hours ago. "How do you know about that? Only three people in the world know about that mark, and two of them are dead."

"We know everything, Elena Marchetti. We know that you were not meant to survive Karthos. We know that the mark chose you on the battlefield, as you held your dying friend in your arms. We know that you have hidden it ever since, afraid of what it means, afraid of what it might make of you." The figure's voice softened, almost gentle. "We know why you really left the army. It was not the politics. It was not the betrayal. It was the fear of what you were becoming."

The rage that Elena had buried for seven years rose like a tidal wave, hot and overwhelming, burning away her caution and her fear. "You do not know anything," she snarled, the words torn from somewhere deep and wounded. "You were not there. You did not see what I saw. You did not hold him as the light went out of his eyes and feel the exact moment when the soul leaves the body behind."

"I know you blame yourself. I know you think you failed him. But I also know that the Mark chose you for a reason, and that reason is not yet fulfilled." The figure closed the book, and the blue flame died. "The new moon rises tonight, Captain. And when it does, the Veil will thin, and the things that wait on the other side will come through. Your choice is simple: stand with us, or watch this city burn."

The symbol on Elena's chest, the mark she had hidden since Karthos beneath bandages and shame, began to burn. Not with heat, but with light — a golden radiance that pushed back the shadows and illuminated the vast chamber around her.

"It is awakening," the figure whispered, and there was something like awe in their voice. "After three hundred years, it awakens again."

Elena looked down at her chest, where the light was brightest, and felt the weight of destiny settle on her shoulders like a mantle she had never wanted and could never refuse.

She thought of Kaelen. She thought of the promise she had made.

And she made her choice.

End of Sample."""
            with open(sample_path, 'w') as f:
                f.write(sample_text)
        return str(sample_path)
