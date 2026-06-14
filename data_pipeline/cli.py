#!/usr/bin/env python3
import argparse
import sys
import logging
from pathlib import Path

from data_pipeline.orchestrator import PipelineOrchestrator
from data_pipeline.config import DEFAULT_PIPELINE_CONFIG


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser(
        description="SCRIPTY Narrative Corpus Extraction Pipeline v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process a single file:
    python -m data_pipeline.cli --input novel.txt

  Process all files in a directory:
    python -m data_pipeline.cly --input-dir data/gutenberg/

  Process multiple files:
    python -m data_pipeline.cli --inputs book1.txt book2.epub book3.pdf

  Process and limit fragments:
    python -m data_pipeline.cli --input-dir data/ --max-fragments 50000

  Generate sample data and test:
    python -m data_pipeline.cli --sample
        """,
    )

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--input', '-i',
        type=str,
        help='Single input file path',
    )
    input_group.add_argument(
        '--input-dir', '-d',
        type=str,
        default=None,
        help='Directory containing input files',
    )
    input_group.add_argument(
        '--inputs', '-I',
        type=str, nargs='+',
        help='Multiple input file paths',
    )
    input_group.add_argument(
        '--sample', '-s',
        action='store_true',
        help='Run pipeline with sample data only',
    )

    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=DEFAULT_PIPELINE_CONFIG["output_dir"],
        help='Output directory for fragments and indexes',
    )
    parser.add_argument(
        '--max-fragments', '-m',
        type=int,
        default=100000,
        help='Maximum number of fragments to produce (default: 100000)',
    )
    parser.add_argument(
        '--min-quality',
        type=float,
        default=0.60,
        help='Minimum quality score threshold (default: 0.60)',
    )
    parser.add_argument(
        '--skip-dedup',
        action='store_true',
        help='Skip deduplication step',
    )
    parser.add_argument(
        '--skip-rag',
        action='store_true',
        help='Skip RAG preparation',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging',
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = {
        "output_dir": args.output_dir,
        "report_dir": str(Path(args.output_dir) / "reports"),
        "fragment_store": str(Path(args.output_dir) / "fragments.jsonl"),
        "elite_store": str(Path(args.output_dir) / "elite_fragments.jsonl"),
        "character_memory_store": str(Path(args.output_dir) / "character_memory_fragments.jsonl"),
        "foreshadowing_graph": str(Path(args.output_dir) / "foreshadowing_graph.json"),
        "scene_blueprints": str(Path(args.output_dir) / "scene_blueprints.jsonl"),
        "faiss_index_path": str(Path(args.output_dir) / "faiss_index"),
        "corpus_jsonl": str(Path(args.output_dir) / "rag_corpus.jsonl"),
    }

    orchestrator = PipelineOrchestrator(config)

    input_paths = []
    if args.sample:
        logger.info("Running with sample data")
    elif args.input:
        input_paths = [args.input]
    elif args.inputs:
        input_paths = args.inputs
    elif args.input_dir:
        input_dir = args.input_dir
    else:
        parser.print_help()
        sys.exit(1)

    input_dir = getattr(args, 'input_dir', None)

    try:
        results = orchestrator.run(input_paths=input_paths, input_dir=input_dir)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)

    if results.get("status") == "success":
        print(f"\n{'=' * 60}")
        print(f"PIPELINE COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Fragments:     {results['total_fragments']}")
        print(f"  Elite:         {results['elite_fragments']}")
        print(f"  Books:         {results['unique_books']}")
        print(f"  Categories:    {results['categories_covered']}")
        print(f"  Time:          {results['elapsed_seconds']:.1f}s")
        print(f"  Output:        {args.output_dir}")
        print(f"{'=' * 60}")
    else:
        print(f"Pipeline error: {results.get('message', 'Unknown error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
