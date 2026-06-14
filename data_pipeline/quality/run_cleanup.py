#!/usr/bin/env python3
"""
Corpus Cleanup Pipeline

Runs all cleanup modules on existing fragment data:
1. Participant Cleanup
2. Location Cleanup
3. Enhanced Relationship Extraction
4. Scene Role Assignment + Narrative Functions
5. Validation Report Generation

Generates a report at reports/corpus_cleanup_report.md
"""

import sys
import os
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.participant_cleaner import ParticipantCleaner
from data_pipeline.quality.location_cleaner import LocationCleaner
from data_pipeline.quality.scene_role_assigner import SceneRoleAssigner
from data_pipeline.quality.validation_pipeline import ValidationPipeline
from data_pipeline.passes.pass4_relationships import RelationshipExtractionPass


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def load_fragments(path: str) -> List[NarrativeFragment]:
    """Load fragments from a JSONL file."""
    fragments = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                fragments.append(NarrativeFragment.from_dict(data))
    logger.info(f"Loaded {len(fragments)} fragments from {path}")
    return fragments


def save_fragments(fragments: List[NarrativeFragment], path: str):
    """Save fragments to a JSONL file."""
    with open(path, 'w') as f:
        for frag in fragments:
            f.write(frag.to_json() + '\n')
    logger.info(f"Saved {len(fragments)} fragments to {path}")


def compute_initial_stats(fragments: List[NarrativeFragment]) -> Dict[str, Any]:
    """Compute initial quality statistics."""
    total = len(fragments)
    participants_total = sum(len(f.participants) for f in fragments)
    locations_total = sum(1 for f in fragments if f.location)
    scene_roles_total = sum(1 for f in fragments if f.scene_role)
    relationship_types_total = sum(1 for f in fragments if f.relationship_type)
    narrative_functions_total = sum(1 for f in fragments if f.narrative_function)

    # Count garbage participants
    garbage_participants = 0
    for f in fragments:
        for p in f.participants:
            p = p.strip()
            if not p or len(p) == 1 or not p[0].isupper():
                garbage_participants += 1
            elif p.lower() in {
                "the", "this", "that", "these", "those", "what", "which",
                "who", "whom", "when", "where", "why", "how", "all",
                "each", "every", "both", "few", "many", "some", "any",
                "no", "not", "only", "just", "then", "than", "there",
                "here", "into", "upon", "after", "before", "between",
                "through", "during", "without", "within", "along",
                "about", "across", "among", "chapter", "part", "book",
                "volume", "section", "act", "scene",
                "now", "yes", "well", "oh", "ah", "said", "was", "were",
                "had", "been", "being", "having", "doing",
                "one", "two", "three", "four", "five", "first", "second",
                "sir", "lord", "lady", "king", "queen", "prince",
                "captain", "major", "colonel", "general", "doctor",
                "mr", "mrs", "ms", "miss", "dr", "prof",
                "from", "come", "let", "don", "yet", "soon",
                "poor", "dear", "old", "young", "good", "great",
            }:
                garbage_participants += 1

    # Count garbage locations
    garbage_locations = 0
    for f in fragments:
        if f.location:
            loc = f.location.strip().lower()
            if loc in {
                "age", "era", "epoch", "period", "reign", "century",
                "decade", "house", "room", "hall", "chamber", "building",
                "tower", "castle", "palace", "fort", "street", "road",
                "mountain", "hill", "valley", "forest", "lake", "river",
                "sea", "ocean", "city", "town", "village", "port",
                "garden", "tree", "flower", "sky", "field",
                "entrance", "gate", "door", "wall", "bridge",
                "square", "quarter", "capital", "machine",
            }:
                garbage_locations += 1

    return {
        "total_fragments": total,
        "total_participants": participants_total,
        "fragments_with_location": locations_total,
        "fragments_with_scene_role": scene_roles_total,
        "fragments_with_relationship_type": relationship_types_total,
        "fragments_with_narrative_function": narrative_functions_total,
        "garbage_participants": garbage_participants,
        "garbage_locations": garbage_locations,
    }


def main():
    # Configuration
    output_dir = Path(__file__).resolve().parent.parent / "output"
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    input_path = output_dir / "fragments_deduplicated.jsonl"
    output_clean_path = output_dir / "fragments_cleaned.jsonl"
    output_backup_path = output_dir / "fragments_cleanup_backup.jsonl"

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    logger.info("=" * 60)
    logger.info("SCRIPTY CORPUS CLEANUP PIPELINE")
    logger.info("=" * 60)

    # Load fragments
    fragments = load_fragments(str(input_path))
    initial_stats = compute_initial_stats(fragments)

    logger.info(f"\nInitial state:")
    logger.info(f"  Total fragments: {initial_stats['total_fragments']}")
    logger.info(f"  Total participants: {initial_stats['total_participants']}")
    logger.info(f"  Garbage participants: {initial_stats['garbage_participants']}")
    logger.info(f"  Garbage locations: {initial_stats['garbage_locations']}")
    logger.info(f"  With scene_roles: {initial_stats['fragments_with_scene_role']}")
    logger.info(f"  With relationship_types: {initial_stats['fragments_with_relationship_type']}")
    logger.info(f"  With narrative_functions: {initial_stats['fragments_with_narrative_function']}")

    # Create backup
    save_fragments(fragments, str(output_backup_path))

    start_time = time.time()
    steps = []

    # Step 1: Enhanced Relationship Extraction
    logger.info("\n--- Step 1: Enhanced Relationship Extraction ---")
    rel_extractor = RelationshipExtractionPass()
    rel_before = initial_stats['fragments_with_relationship_type']
    fragments = rel_extractor.execute(fragments)
    rel_after = sum(1 for f in fragments if f.relationship_type)
    steps.append({
        "name": "Relationship Extraction",
        "before": rel_before,
        "after": rel_after,
        "delta": rel_after - rel_before,
    })

    # Step 2: Participant Cleanup
    logger.info("\n--- Step 2: Participant Cleanup ---")
    participant_cleaner = ParticipantCleaner()
    part_before = initial_stats['garbage_participants']
    fragments = participant_cleaner.clean_fragments(fragments)
    steps.append({
        "name": "Participant Cleanup",
        "before": part_before,
        "after": participant_cleaner.get_stats()["invalid_removed"],
        "delta": part_before - participant_cleaner.get_stats()["invalid_removed"],
    })

    # Step 3: Location Cleanup
    logger.info("\n--- Step 3: Location Cleanup ---")
    location_cleaner = LocationCleaner()
    loc_before = initial_stats['garbage_locations']
    fragments = location_cleaner.clean_fragments(fragments)
    steps.append({
        "name": "Location Cleanup",
        "before": loc_before,
        "after": location_cleaner.get_stats()["invalid_locations"],
        "delta": loc_before - location_cleaner.get_stats()["invalid_locations"],
    })

    # Step 4: Scene Role Assignment
    logger.info("\n--- Step 4: Scene Role Assignment ---")
    scene_assigner = SceneRoleAssigner()
    sr_before = initial_stats['fragments_with_scene_role']
    fragments = scene_assigner.assign_roles(fragments)
    sr_after = sum(1 for f in fragments if f.scene_role)
    steps.append({
        "name": "Scene Role Assignment",
        "before": sr_before,
        "after": sr_after,
        "delta": sr_after - sr_before,
    })

    # Step 5: Narrative Function Assignment
    logger.info("\n--- Step 5: Narrative Function Assignment ---")
    nf_before = initial_stats['fragments_with_narrative_function']
    fragments = scene_assigner.assign_narrative_functions(fragments)
    nf_after = sum(1 for f in fragments if f.narrative_function)
    steps.append({
        "name": "Narrative Function Assignment",
        "before": nf_before,
        "after": nf_after,
        "delta": nf_after - nf_before,
    })

    # Step 6: Validation
    logger.info("\n--- Step 6: Validation ---")
    validator = ValidationPipeline()
    report = validator.run_validation(fragments)
    summary = validator.get_summary(report)

    elapsed = time.time() - start_time

    # Save cleaned fragments
    save_fragments(fragments, str(output_clean_path))

    # Compute final stats
    final_stats = compute_initial_stats(fragments)

    # Generate report
    generate_report(
        reports_dir / "corpus_cleanup_report.md",
        initial_stats,
        final_stats,
        steps,
        report,
        participant_cleaner.get_stats(),
        location_cleaner.get_stats(),
        scene_assigner.get_stats(),
        rel_extractor.get_stats(),
        elapsed,
        summary,
    )

    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP COMPLETE")
    logger.info(f"Elapsed: {elapsed:.2f}s")
    logger.info(f"Cleaned fragments saved to: {output_clean_path}")
    logger.info(f"Report saved to: {reports_dir / 'corpus_cleanup_report.md'}")
    logger.info(f"Backup saved to: {output_backup_path}")
    logger.info("=" * 60)

    # Print validation summary
    print()
    print(summary)


def generate_report(
    report_path: Path,
    initial_stats: Dict[str, Any],
    final_stats: Dict[str, Any],
    steps: List[Dict[str, Any]],
    validation_report: Dict[str, Any],
    participant_stats: Dict[str, Any],
    location_stats: Dict[str, Any],
    scene_stats: Dict[str, Any],
    rel_stats: Dict[str, Any],
    elapsed: float,
    summary: str,
):
    """Generate a comprehensive cleanup report in Markdown."""

    rates = validation_report.get("rates", {})
    success = validation_report.get("success", {})

    # Compute improvement
    part_improvement = initial_stats["garbage_participants"] - final_stats["garbage_participants"]
    loc_improvement = initial_stats["garbage_locations"] - final_stats["garbage_locations"]
    sr_improvement = final_stats["fragments_with_scene_role"] - initial_stats["fragments_with_scene_role"]
    rt_improvement = final_stats["fragments_with_relationship_type"] - initial_stats["fragments_with_relationship_type"]
    nf_improvement = final_stats["fragments_with_narrative_function"] - initial_stats["fragments_with_narrative_function"]

    report_lines = [
        "# Corpus Cleanup Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Pipeline Time:** {elapsed:.2f}s",
        f"**Fragments Processed:** {initial_stats['total_fragments']}",
        "",
        "---",
        "",
        "## 1. Summary",
        "",
        "| Metric | Before | After | Improvement |",
        "|--------|--------|-------|-------------|",
        f"| Garbage Participants | {initial_stats['garbage_participants']} | {final_stats['garbage_participants']} | **+{part_improvement} removed** |",
        f"| Garbage Locations | {initial_stats['garbage_locations']} | {final_stats['garbage_locations']} | **+{loc_improvement} removed** |",
        f"| Fragments with Scene Roles | {initial_stats['fragments_with_scene_role']} | {final_stats['fragments_with_scene_role']} | **+{sr_improvement} filled** |",
        f"| Fragments with Relationship Types | {initial_stats['fragments_with_relationship_type']} | {final_stats['fragments_with_relationship_type']} | **+{rt_improvement} filled** |",
        f"| Fragments with Narrative Functions | {initial_stats['fragments_with_narrative_function']} | {final_stats['fragments_with_narrative_function']} | **+{nf_improvement} filled** |",
        "",
        "---",
        "",
        "## 2. Step-by-Step Results",
        "",
    ]

    for step in steps:
        report_lines.extend([
            f"### {step['name']}",
            "",
            f"- **Before:** {step['before']}",
            f"- **After:** {step['after']}",
            f"- **Delta:** {step['delta']:+d}",
            "",
        ])

    report_lines.extend([
        "---",
        "",
        "## 3. Validation Results",
        "",
        f"### Quality Rates",
        "",
        "| Metric | Value | Target | Status |",
        "|--------|-------|--------|--------|",
        f"| Invalid Participants | {rates.get('invalid_participants_pct', 0):.2f}% | <5% | {'✅ PASS' if success.get('invalid_participants') else '❌ FAIL'} |",
        f"| Invalid Locations | {rates.get('invalid_locations_pct', 0):.2f}% | <2% | {'✅ PASS' if success.get('invalid_locations') else '❌ FAIL'} |",
        f"| Invalid (Character-in-Participants) | {rates.get('invalid_locations_detail', 'N/A')} | — | — |",
        f"| Scene Roles Populated | {rates.get('scene_role_populated_pct', 0):.2f}% | >95% | {'✅ PASS' if rates.get('scene_role_populated_pct', 0) > 95 else '❌ FAIL'} |",
        f"| Relationship Types Populated | {rates.get('relationship_type_populated_pct', 0):.2f}% | — | — |",
        f"| Narrative Functions Populated | {rates.get('narrative_function_populated_pct', 0):.2f}% | >95% | {'✅ PASS' if rates.get('narrative_function_populated_pct', 0) > 95 else '❌ FAIL'} |",
        "",
        f"**Overall: {'✅ ALL CHECKS PASSED' if success.get('overall') else '❌ SOME CHECKS FAILED'}**",
        "",
        "---",
        "",
        "## 4. Detailed Statistics",
        "",
        "### Participant Cleaner Stats",
        "",
        f"- Participants checked: {participant_stats.get('total_participants_checked', 0)}",
        f"- Invalid removed: {participant_stats.get('invalid_removed', 0)}",
        f"- Fragments affected: {participant_stats.get('fragments_cleaned', 0)}",
        f"- Removal rate: {participant_stats.get('removal_rate', 0):.2f}%",
        "",
        "#### Top Removed Participants",
        "",
    ])

    for name, count in participant_stats.get("most_removed", {}).items():
        report_lines.append(f"- `{name}`: {count} times")

    report_lines.extend([
        "",
        "#### Removed by Reason",
        "",
    ])
    for reason, count in participant_stats.get("removed_by_reason", {}).items():
        report_lines.append(f"- {reason}: {count}")
    report_lines.append("")

    report_lines.extend([
        "### Location Cleaner Stats",
        "",
        f"- Locations checked: {location_stats.get('total_locations_checked', 0)}",
        f"- Invalid locations: {location_stats.get('invalid_locations', 0)}",
        f"- Invalid rate: {location_stats.get('invalid_rate', 0):.2f}%",
        f"- Fragments affected: {location_stats.get('fragments_cleaned', 0)}",
        "",
        "#### Top Invalid Locations",
        "",
    ])

    for loc, count in location_stats.get("most_common_invalid", {}).items():
        report_lines.append(f"- `{loc}`: {count} times")
    report_lines.append("")

    report_lines.extend([
        "### Scene Role Assigner Stats",
        "",
        f"- Fragments processed: {scene_stats.get('fragments_processed', 0)}",
        f"- Roles assigned: {scene_stats.get('roles_assigned', 0)}",
        f"- Existing kept: {scene_stats.get('existing_kept', 0)}",
        "",
        "#### Roles Distribution",
        "",
    ])

    for role, count in scene_stats.get("by_role", {}).items():
        report_lines.append(f"- {role}: {count}")
    report_lines.append("")

    report_lines.extend([
        "### Relationship Extraction Stats",
        "",
        f"- Fragments processed: {rel_stats.get('fragments_processed', 0)}",
        f"- Relationships detected: {rel_stats.get('relationships_detected', 0)}",
        "",
        "#### By Type",
        "",
    ])

    for rtype, count in rel_stats.get("by_type", {}).items():
        report_lines.append(f"- {rtype}: {count}")

    report_lines.extend([
        "",
        "#### By Detection Method",
        "",
    ])

    for method, count in rel_stats.get("by_method", {}).items():
        report_lines.append(f"- {method}: {count}")

    report_lines.extend([
        "",
        "---",
        "",
        "## 5. Success Criteria Check",
        "",
        "| Criterion | Threshold | Actual | Status |",
        "|-----------|-----------|--------|--------|",
        f"| Invalid Participants | <5% | {rates.get('invalid_participants_pct', 0):.2f}% | {'✅ PASS' if success.get('invalid_participants') else '❌ FAIL'} |",
        f"| Invalid Locations | <2% | {rates.get('invalid_locations_pct', 0):.2f}% | {'✅ PASS' if success.get('invalid_locations') else '❌ FAIL'} |",
        f"| Scene Roles Populated | >95% | {rates.get('scene_role_populated_pct', 0):.2f}% | {'✅ PASS' if rates.get('scene_role_populated_pct', 0) > 95 else '❌ FAIL'} |",
        f"| Narrative Functions Populated | >95% | {rates.get('narrative_function_populated_pct', 0):.2f}% | {'✅ PASS' if rates.get('narrative_function_populated_pct', 0) > 95 else '❌ FAIL'} |",
        "",
        f"**Overall Result: {'✅ PASS' if success.get('overall') else '❌ FAIL'}**",
        "",
    ])

    report_path.write_text("\n".join(report_lines))
    logger.info(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
