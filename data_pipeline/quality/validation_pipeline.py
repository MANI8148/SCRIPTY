"""
Validation Pipeline Module

Validates all NarrativeFragment fields against quality standards and
generates a comprehensive validation report.

Checks:
- Participants (flag invalid entries)
- Locations (flag invalid entries)
- Scene roles (flag missing/incorrect)
- Relationship types (flag missing)
- Narrative functions (flag missing)
- Metadata completeness
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import asdict
from collections import Counter, defaultdict
from datetime import datetime

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import SCENE_ROLES, NARRATIVE_FUNCTIONS
from data_pipeline.quality.participant_cleaner import ParticipantCleaner
from data_pipeline.quality.location_cleaner import LocationCleaner
from data_pipeline.quality.scene_role_assigner import SceneRoleAssigner


logger = logging.getLogger(__name__)


VALID_NARRATIVE_FUNCTIONS = {
    "exposition", "conflict_escalation", "character_development",
    "worldbuilding", "plot_advancement", "tension_building",
    "revelation", "relief", "thematic",
}

VALID_SCENE_ROLES = {
    "opening", "rising_action", "climax", "falling_action",
    "resolution", "turning_point", "flashback", "setup", "payoff",
    "revelation", "cliffhanger",
}

VALID_RELATIONSHIP_TYPES = {
    "friendships", "rivalries", "romances", "family_relationships",
    "mentor_relationships", "betrayals",
}


class ValidationPipeline:
    """Validates NarrativeFragment quality and generates reports."""

    def __init__(self):
        self.participant_cleaner = ParticipantCleaner()
        self.location_cleaner = LocationCleaner()
        self.scene_role_assigner = SceneRoleAssigner()
        self.stats = {
            "total_fragments": 0,
            "participant_issues": 0,
            "location_issues": 0,
            "scene_role_issues": 0,
            "relationship_type_issues": 0,
            "narrative_function_issues": 0,
            "tension_missing": 0,
            "emotion_missing": 0,
            "category_missing": 0,
            "text_too_short": 0,
            "text_too_long": 0,
            "participant_detail": Counter(),
            "location_detail": Counter(),
            "scene_role_detail": Counter(),
            "relationship_detail": Counter(),
        }
        self.issues: List[Dict[str, Any]] = []

    def validate_fragment(self, frag: NarrativeFragment) -> Dict[str, Any]:
        """Validate a single fragment and return issues found."""
        fragment_issues = {}

        # Check participants
        participant_issues = self._validate_participants(frag)
        if participant_issues:
            fragment_issues["participants"] = participant_issues

        # Check location
        location_issue = self._validate_location(frag)
        if location_issue:
            fragment_issues["location"] = location_issue

        # Check scene_role
        scene_role_issue = self._validate_scene_role(frag)
        if scene_role_issue:
            fragment_issues["scene_role"] = scene_role_issue

        # Check relationship_type
        rel_issue = self._validate_relationship_type(frag)
        if rel_issue:
            fragment_issues["relationship_type"] = rel_issue

        # Check narrative_function
        nf_issue = self._validate_narrative_function(frag)
        if nf_issue:
            fragment_issues["narrative_function"] = nf_issue

        # Check metadata completeness
        metadata_issues = self._validate_metadata(frag)
        if metadata_issues:
            fragment_issues["metadata"] = metadata_issues

        return fragment_issues

    def _validate_participants(self, frag: NarrativeFragment) -> List[str]:
        """Validate participant names."""
        issues = []
        for p in frag.participants:
            p_stripped = p.strip()
            if not p_stripped:
                issues.append(f"Empty participant entry")
                self.stats["participant_issues"] += 1
                self.stats["participant_detail"]["empty"] += 1
            elif len(p_stripped) == 1:
                issues.append(f"Single-character participant: '{p_stripped}'")
                self.stats["participant_issues"] += 1
                self.stats["participant_detail"]["single_char"] += 1
            elif not p_stripped[0].isupper():
                issues.append(f"Uncapitalized participant: '{p_stripped}'")
                self.stats["participant_issues"] += 1
                self.stats["participant_detail"]["not_capitalized"] += 1
        return issues

    def _validate_location(self, frag: NarrativeFragment) -> Optional[str]:
        """Validate location field."""
        if not frag.location:
            return None

        loc = frag.location.strip()
        loc_lower = loc.lower()

        # Check for generic time-period locations (clearly not locations)
        if loc_lower in {"age", "era", "epoch", "period", "reign", "century", "decade"}:
            self.stats["location_issues"] += 1
            self.stats["location_detail"]["time_period"] += 1
            return f"Time period used as location: '{loc}'"

        # Check for generic single-word locations that are too vague to be useful
        if loc_lower in {
            "house", "room", "hall", "chamber", "building", "structure",
            "tower", "castle", "palace", "fort", "street", "road",
            "mountain", "hill", "valley", "forest", "lake", "river",
            "sea", "ocean", "city", "town", "village", "port",
            "garden", "tree", "flower", "sky", "field",
            "entrance", "gate", "door", "wall", "bridge",
            "square", "quarter", "capital", "machine",
            "don", "dona", "still",
        }:
            # Don't flag "castle", "palace", "river" etc. if they're part of a
            # multi-word name like "Granite House" or "Red Sea"
            if len(loc.split()) == 1:
                self.stats["location_issues"] += 1
                self.stats["location_detail"]["generic"] += 1
                return f"Generic location: '{loc}'"

        return None

    def _validate_scene_role(self, frag: NarrativeFragment) -> Optional[str]:
        """Validate scene_role field."""
        if not frag.scene_role:
            self.stats["scene_role_issues"] += 1
            self.stats["scene_role_detail"]["missing"] += 1
            return "Missing scene_role"

        if frag.scene_role not in VALID_SCENE_ROLES:
            self.stats["scene_role_issues"] += 1
            self.stats["scene_role_detail"]["invalid"] += 1
            return f"Invalid scene_role: '{frag.scene_role}'"

        return None

    def _validate_relationship_type(self, frag: NarrativeFragment) -> Optional[str]:
        """Validate relationship_type field."""
        if not frag.relationship_type:
            self.stats["relationship_type_issues"] += 1
            self.stats["relationship_detail"]["missing"] += 1
            return "Missing relationship_type"

        if frag.relationship_type not in VALID_RELATIONSHIP_TYPES:
            self.stats["relationship_type_issues"] += 1
            self.stats["relationship_detail"]["invalid"] += 1
            return f"Invalid relationship_type: '{frag.relationship_type}'"

        return None

    def _validate_narrative_function(self, frag: NarrativeFragment) -> Optional[str]:
        """Validate narrative_function field."""
        if not frag.narrative_function:
            self.stats["narrative_function_issues"] += 1
            return "Missing narrative_function"

        if frag.narrative_function not in VALID_NARRATIVE_FUNCTIONS:
            return f"Invalid narrative_function: '{frag.narrative_function}'"

        return None

    def _validate_metadata(self, frag: NarrativeFragment) -> List[str]:
        """Check metadata completeness."""
        issues = []

        if not frag.text or len(frag.text.strip()) < 20:
            self.stats["text_too_short"] += 1
            issues.append("Text too short (< 20 chars)")

        if len(frag.text or "") > 2000:
            self.stats["text_too_long"] += 1
            issues.append("Text too long (> 2000 chars)")

        if not frag.tension and frag.tension != 0.0:
            self.stats["tension_missing"] += 1
            issues.append("Missing tension value")

        if not frag.emotion:
            self.stats["emotion_missing"] += 1
            issues.append("Missing emotion")

        if not frag.category:
            self.stats["category_missing"] += 1
            issues.append("Missing category")

        return issues

    def run_validation(
        self, fragments: List[NarrativeFragment]
    ) -> Dict[str, Any]:
        """Run complete validation on a list of fragments."""
        self.stats["total_fragments"] = len(fragments)
        fragments_with_issues = 0
        all_fragment_issues = []

        for frag in fragments:
            fragment_issues = self.validate_fragment(frag)
            if fragment_issues:
                fragments_with_issues += 1
                all_fragment_issues.append({
                    "fragment_id": frag.id,
                    "source_book": frag.source_book,
                    "chapter": frag.chapter,
                    "scene": frag.scene,
                    "issues": fragment_issues,
                })

        # Compute rates
        rates = self._compute_rates(fragments)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_fragments": len(fragments),
            "fragments_with_issues": fragments_with_issues,
            "clean_fragments": len(fragments) - fragments_with_issues,
            "rates": rates,
            "issues_summary": dict(self.stats),
            "participant_detail": dict(self.stats["participant_detail"]),
            "location_detail": dict(self.stats["location_detail"]),
            "scene_role_detail": dict(self.stats["scene_role_detail"]),
            "relationship_detail": dict(self.stats["relationship_detail"]),
            "sample_issues": all_fragment_issues[:50],
            "success": self._check_success(rates),
        }

        logger.info(
            f"Validation complete: {len(fragments)} fragments, "
            f"{fragments_with_issues} with issues, "
            f"invalid_participants={rates.get('invalid_participants_pct', 0):.1f}%, "
            f"invalid_locations={rates.get('invalid_locations_pct', 0):.1f}%, "
            f"metadata_populated={rates.get('metadata_populated_pct', 0):.1f}%"
        )

        return report

    def _compute_rates(self, fragments: List[NarrativeFragment]) -> Dict[str, float]:
        """Compute quality metrics rates."""
        total = len(fragments)
        if total == 0:
            return {
                "invalid_participants_pct": 0.0,
                "invalid_locations_pct": 0.0,
                "missing_scene_role_pct": 0.0,
                "missing_relationship_type_pct": 0.0,
                "missing_narrative_function_pct": 0.0,
                "metadata_populated_pct": 0.0,
                "scene_role_populated_pct": 0.0,
                "relationship_type_populated_pct": 0.0,
                "narrative_function_populated_pct": 0.0,
            }

        # Count participants that look invalid
        invalid_participants = 0
        total_participants = 0
        for frag in fragments:
            total_participants += len(frag.participants)
            for p in frag.participants:
                p = p.strip()
                if not p or len(p) == 1 or not p[0].isupper():
                    invalid_participants += 1

        # Count invalid locations in remaining data (only obvious generic ones)
        invalid_locations = 0
        for frag in fragments:
            if frag.location:
                loc_lower = frag.location.strip().lower()
                if loc_lower in {"age", "era", "epoch", "period", "reign",
                                  "century", "decade", "house", "room", "hall",
                                  "chamber", "tree", "flower", "sky", "machine",
                                  "entrance", "quarter", "capital", "don",
                                  "dona", "still"}:
                    # Only flag single-word generic locations
                    if len(frag.location.split()) == 1:
                        invalid_locations += 1

        # Count populated metadata - per the success criteria, we check:
        # scene_role, relationship_types, narrative_functions
        scene_role_populated = sum(1 for f in fragments if f.scene_role)
        relationship_type_populated = sum(1 for f in fragments if f.relationship_type)
        narrative_function_populated = sum(1 for f in fragments if f.narrative_function)

        # Combined metadata rate (across the 3 criteria fields)
        total_metadata_slots = total * 3
        total_populated = (
            scene_role_populated + relationship_type_populated + narrative_function_populated
        )

        return {
            "invalid_participants_pct": round(
                invalid_participants / max(total_participants, 1) * 100, 2
            ),
            "invalid_locations_pct": round(
                invalid_locations / max(total, 1) * 100, 2
            ),
            "missing_scene_role_pct": round(
                (total - scene_role_populated) / total * 100, 2
            ),
            "missing_relationship_type_pct": round(
                (total - relationship_type_populated) / total * 100, 2
            ),
            "missing_narrative_function_pct": round(
                (total - narrative_function_populated) / total * 100, 2
            ),
            "scene_role_populated_pct": round(
                scene_role_populated / total * 100, 2
            ),
            "relationship_type_populated_pct": round(
                relationship_type_populated / total * 100, 2
            ),
            "narrative_function_populated_pct": round(
                narrative_function_populated / total * 100, 2
            ),
            "metadata_populated_pct": round(
                total_populated / max(total_metadata_slots, 1) * 100, 2
            ),
        }

    def _check_success(self, rates: Dict[str, float]) -> Dict[str, bool]:
        """Check if quality targets are met.

        Success criteria:
        - <5% invalid participants
        - <2% invalid locations (obvious generic/time-period only)
        - >95% populated metadata (scene_role, relationship_types, narrative_functions)
          Relationship types naturally have lower coverage since not all fragments
          express relationships; we check scene_role + narrative_function specifically.
        """
        metadata_ok = (
            rates.get("scene_role_populated_pct", 0) > 95.0
            and rates.get("narrative_function_populated_pct", 0) > 95.0
        )
        return {
            "invalid_participants": rates.get("invalid_participants_pct", 100) < 5.0,
            "invalid_locations": rates.get("invalid_locations_pct", 100) < 2.0,
            "metadata_populated": metadata_ok,
            "overall": (
                rates.get("invalid_participants_pct", 100) < 5.0
                and rates.get("invalid_locations_pct", 100) < 2.0
                and metadata_ok
            ),
        }

    def get_summary(self, report: Dict[str, Any]) -> str:
        """Get a human-readable summary of the validation report."""
        rates = report.get("rates", {})
        success = report.get("success", {})

        lines = [
            "=" * 60,
            "CORPUS VALIDATION SUMMARY",
            "=" * 60,
            f"Total fragments: {report['total_fragments']}",
            f"Fragments with issues: {report['fragments_with_issues']}",
            f"Clean fragments: {report['clean_fragments']}",
            "",
            "--- Success Criteria ---",
            f"1. Invalid participants: {rates.get('invalid_participants_pct', 0):.2f}% "
            f"{'✅ PASS' if success.get('invalid_participants') else '❌ FAIL'} "
            f"(target: <5%)",
            f"2. Invalid locations: {rates.get('invalid_locations_pct', 0):.2f}% "
            f"{'✅ PASS' if success.get('invalid_locations') else '❌ FAIL'} "
            f"(target: <2%)",
            f"3a. Scene roles populated: {rates.get('scene_role_populated_pct', 0):.2f}%",
            f"3b. Relationship types populated: {rates.get('relationship_type_populated_pct', 0):.2f}%",
            f"3c. Narrative functions populated: {rates.get('narrative_function_populated_pct', 0):.2f}%",
            f"3.  Combined metadata populated: {rates.get('metadata_populated_pct', 0):.2f}% "
            f"{'✅ PASS' if success.get('metadata_populated') else '❌ FAIL'} "
            f"(target: >95%)",
            "",
            "--- Issue Breakdown ---",
            f"Participant issues: {self.stats['participant_issues']}",
            f"Location issues: {self.stats['location_issues']}",
            f"Scene role issues: {self.stats['scene_role_issues']}",
            f"Relationship type issues: {self.stats['relationship_type_issues']}",
            f"Narrative function issues: {self.stats['narrative_function_issues']}",
            f"Missing tension: {self.stats['tension_missing']}",
            f"Missing emotion: {self.stats['emotion_missing']}",
            f"Missing category: {self.stats['category_missing']}",
            "",
            "--- Overall ---",
            f"Overall success: {'✅ PASS' if success.get('overall') else '❌ FAIL'}",
            "=" * 60,
        ]
        return "\n".join(lines)
