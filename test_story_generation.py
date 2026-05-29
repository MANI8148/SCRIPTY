#!/usr/bin/env python3
"""
Comprehensive story generation test script.
Tests various genres, locations, time periods, and chapter counts.
"""
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.narrative_engine import NarrativeEngine
from backend.research.memory_manager import MemoryManager
from backend.research.narrative_planner import NarrativePlanner
from backend.research.rag_pipeline import RAGPipeline
from backend.research.evaluation_pipeline import EvaluationPipeline
from backend.research.experiment_tracker import ExperimentTracker


def test_story_generation():
    """Test story generation with various inputs."""
    
    # Test configurations
    test_cases = [
        {
            "name": "Historical Fiction - Colonial India",
            "location": "Delhi",
            "year": 1857,
            "chapter_count": 3,
            "genre": "Historical Fiction",
            "theme": "rebellion",
            "random_seed": 42
        },
        {
            "name": "Mystery - Victorian London",
            "location": "London",
            "year": 1888,
            "chapter_count": 3,
            "genre": "Mystery",
            "theme": "investigation",
            "random_seed": 43
        },
        {
            "name": "Adventure - Ancient Egypt",
            "location": "Cairo",
            "year": 1350,
            "chapter_count": 3,
            "genre": "Adventure",
            "theme": "discovery",
            "random_seed": 44
        },
        {
            "name": "Gothic - Medieval Europe",
            "location": "Prague",
            "year": 1450,
            "chapter_count": 3,
            "genre": "Gothic",
            "theme": "darkness",
            "random_seed": 45
        },
        {
            "name": "Social Fiction - Industrial Revolution",
            "location": "Manchester",
            "year": 1840,
            "chapter_count": 3,
            "genre": "Social Fiction",
            "theme": "class struggle",
            "random_seed": 46
        }
    ]
    
    results = []
    
    print("=" * 80)
    print("SCRIPTY COMPREHENSIVE STORY GENERATION TEST")
    print("=" * 80)
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"Location: {test_case['location']}")
        print(f"Year: {test_case['year']}")
        print(f"Genre: {test_case['genre']}")
        print(f"Theme: {test_case['theme']}")
        print(f"Chapters: {test_case['chapter_count']}")
        print(f"Random Seed: {test_case['random_seed']}")
        print()
        
        try:
            # Initialize engine with all subsystems
            engine = NarrativeEngine(
                memory_manager=MemoryManager(),
                planner=NarrativePlanner(genre=test_case['genre']),
                rag_pipeline=RAGPipeline(manifest_path="backend/data/test_manifest_fixture.jsonl"),
                evaluation_pipeline=EvaluationPipeline(),
                experiment_tracker=ExperimentTracker(log_path=f"backend/research_output/test_experiments.jsonl"),
                output_dir="backend/research_output/test_stories"
            )
            
            # Generate book
            print("Generating story...")
            result = engine.generate_book(
                location=test_case['location'],
                year=test_case['year'],
                chapter_count=test_case['chapter_count'],
                genre=test_case['genre'],
                theme=test_case['theme'],
                random_seed=test_case['random_seed']
            )
            
            # Extract metrics
            chapters = result.get('chapters', [])
            evaluation = result.get('evaluation', {})
            metrics = evaluation.get('metrics', {})
            session_id = result.get('session_id', 'unknown')
            
            # Print results
            print(f"✅ SUCCESS - Generated {len(chapters)} chapters")
            print(f"Session ID: {session_id}")
            print()
            
            # Print chapter summaries
            print("CHAPTERS:")
            for j, chapter in enumerate(chapters, 1):
                print(f"  {j}. {chapter.title}")
                print(f"     Scenes: {len(chapter.scenes)}, Words: {chapter.word_count}")
            print()
            
            # Print evaluation metrics
            print("EVALUATION METRICS:")
            print(f"  Repetition Rate: {metrics.get('repetition_rate', 0):.4f}")
            print(f"  Character Consistency: {metrics.get('character_consistency', 0):.4f}")
            print(f"  Narrative Coherence: {metrics.get('narrative_coherence', 0):.4f}")
            print(f"  Genre Adherence: {metrics.get('genre_adherence', 0):.4f}")
            print(f"  Plan Adherence: {metrics.get('plan_adherence', 0):.4f}")
            print(f"  Graph Connectivity: {metrics.get('graph_connectivity', 0):.4f}")
            print(f"  Retrieval Grounding: {metrics.get('retrieval_grounding', 0):.4f}")
            print()
            
            # Store result
            results.append({
                "test_case": test_case['name'],
                "status": "SUCCESS",
                "chapters": len(chapters),
                "total_words": sum(c.word_count for c in chapters),
                "metrics": metrics,
                "session_id": session_id
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_case": test_case['name'],
                "status": "FAILED",
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(successful/len(results)*100):.1f}%")
    print()
    
    if successful > 0:
        print("AGGREGATE METRICS (Successful Tests):")
        avg_chapters = sum(r.get('chapters', 0) for r in results if r['status'] == 'SUCCESS') / successful
        avg_words = sum(r.get('total_words', 0) for r in results if r['status'] == 'SUCCESS') / successful
        
        print(f"  Average Chapters: {avg_chapters:.1f}")
        print(f"  Average Total Words: {avg_words:.0f}")
        
        # Average metrics
        metric_keys = ['repetition_rate', 'character_consistency', 'narrative_coherence', 
                      'genre_adherence', 'plan_adherence', 'graph_connectivity', 'retrieval_grounding']
        
        for key in metric_keys:
            values = [r['metrics'].get(key, 0) for r in results if r['status'] == 'SUCCESS' and 'metrics' in r]
            if values:
                avg = sum(values) / len(values)
                print(f"  Average {key.replace('_', ' ').title()}: {avg:.4f}")
    
    # Save detailed results
    output_file = Path("backend/research_output/test_generation_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2, default=str), encoding='utf-8')
    print(f"\nDetailed results saved to: {output_file}")
    
    return successful == len(results)


if __name__ == "__main__":
    success = test_story_generation()
    sys.exit(0 if success else 1)
