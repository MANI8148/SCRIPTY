from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.utils.india_timeline import IndiaTimeline
from backend.v2.types import WorldConstraints

if TYPE_CHECKING:
    from backend.external.location_engine import LocationEngine


class LazyLocationEngine:
    """Proxy that lazily imports and delegates to LocationEngine.

    Avoids triggering the slow import chain (Config → load_dotenv → .env)
    during module import. Falls back to minimal location data when the
    import chain fails (e.g., filesystem corruption on curated_lists.py).
    """

    def __init__(self) -> None:
        self._real: object | None = None
        self._fallback = True

    def _get(self) -> object:
        if self._real is None:
            try:
                from backend.external.location_engine import LocationEngine
                self._real = LocationEngine()
                self._fallback = False
            except Exception:
                pass
        return self._real

    async def get_context(self, location_name: str, location_type: str = "urban") -> dict:
        real = self._get()
        if real is not None:
            try:
                return await real.get_context(location_name, location_type)  # type: ignore[union-attr]
            except Exception:
                pass
        return {
            "name": location_name,
            "display_name": location_name,
            "type": location_type,
            "description": f"A {location_type} area known as {location_name}.",
        }


_NOMINATIM_PATTERNS = re.compile(
    r"(recognized as stood|is the capital and|known as the capital|a site that stood as"
    r"|which also known as|stood as the)",
    re.IGNORECASE,
)


def _clean_location_description(description: str, original_name: str) -> str:
    """Sanitize raw API location descriptions into narrative-friendly text.

    Strips Nominatim display_name artifacts and falls back to the original
    location name when the description is ungrammatical API output.
    """
    if not description:
        return original_name

    cleaned = description.strip()

    if _NOMINATIM_PATTERNS.search(cleaned):
        return original_name

    # Strip leading "A urban area known as X" patterns
    area_prefix = re.match(r"^A \w+ area known as (.+?)\.?$", cleaned)
    if area_prefix:
        return area_prefix.group(1).strip()

    # Remove Wikipedia-style parenthetical suffixes: "Hyderabad (city)"
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned)

    # Take only content before first period if unreasonably long
    if len(cleaned) > 80:
        first_sentence = cleaned.split(".")[0]
        if first_sentence:
            cleaned = first_sentence + "."

    return cleaned[:80].strip()


class WorldState:
    """Objective truth about the story world.

    Responsible for producing WorldConstraints that directly constrain
    what the realizer can generate. No metadata-only flows.
    """

    def __init__(
        self,
        location_engine: object | None = None,
    ) -> None:
        self.loc_engine = location_engine or LazyLocationEngine()

    async def build_constraints(
        self,
        location: str,
        year: int,
        location_type: str = "urban",
        active_conflicts: list[str] | None = None,
        unresolved_mysteries: list[str] | None = None,
    ) -> WorldConstraints:
        temporal = IndiaTimeline.get_temporal_context(year)
        loc_data = await self.loc_engine.get_context(location, location_type)
        raw_desc = loc_data.get("description", "")
        clean_desc = _clean_location_description(raw_desc, location)

        return WorldConstraints(
            era=temporal["era"],
            tech_level=temporal["tech"],
            tone=temporal["tone"],
            infrastructure=temporal["infrastructure"],
            transport=temporal["transport"],
            location_description=clean_desc,
            year=year,
            active_conflicts=active_conflicts or [],
            unresolved_mysteries=unresolved_mysteries or [],
        )

    def to_generation_context(self, constraints: WorldConstraints) -> dict[str, str | list[str]]:
        return {
            "era": constraints.era,
            "tech_level": constraints.tech_level,
            "tone": constraints.tone,
            "infrastructure": ", ".join(constraints.infrastructure),
            "transport": ", ".join(constraints.transport),
            "location": constraints.location_description,
            "active_conflicts": constraints.active_conflicts,
            "unresolved_mysteries": constraints.unresolved_mysteries,
        }
