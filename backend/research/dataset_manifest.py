from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PassageRecord:
    passage_id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ManifestEntry:
    source_id: str
    title: str
    author: str
    license: str
    url: str
    passages: list[PassageRecord]
    metadata: dict = field(default_factory=dict)
    source_type: str = "book"
    period: str = "unknown"
    region: str = "global"
    language: str = "en"
    rights_status: str = "public_domain"
    genre: str = "unknown"


REQUIRED_FIELDS = ("source_id", "title", "author", "license", "url", "passages")


def split_passages(source_id: str, text: str, window_tokens: int = 500, stride_tokens: int = 50, metadata: dict | None = None) -> list[PassageRecord]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    step = max(1, window_tokens - stride_tokens)
    passages = []
    for i, start in enumerate(range(0, len(words), step)):
        chunk = words[start:start + window_tokens]
        if not chunk:
            break
        passages.append(PassageRecord(f"{source_id}_p{i:04d}", " ".join(chunk), metadata or {}))
        if start + window_tokens >= len(words):
            break
    return passages


def validate_manifest_entry(raw: dict) -> ManifestEntry | None:
    source_id = raw.get("source_id", "unknown")
    for field_name in REQUIRED_FIELDS:
        if field_name not in raw:
            logger.error("manifest_validation_error", extra={"source_id": source_id, "missing_field": field_name})
            return None
    passages = []
    for item in raw["passages"]:
        if not {"passage_id", "text"}.issubset(item):
            logger.error("manifest_validation_error", extra={"source_id": source_id, "missing_field": "passage_id/text"})
            continue
        passages.append(PassageRecord(item["passage_id"], item["text"], item.get("metadata", {})))
    if not passages:
        return None
    return ManifestEntry(
        raw["source_id"],
        raw["title"],
        raw["author"],
        raw["license"],
        raw["url"],
        passages,
        raw.get("metadata", {}),
        raw.get("source_type", "book"),
        raw.get("period", "unknown"),
        raw.get("region", "global"),
        raw.get("language", "en"),
        raw.get("rights_status", "public_domain"),
        raw.get("genre", "unknown"),
    )


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return []
    entries = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = validate_manifest_entry(json.loads(line))
        if entry is not None:
            entries.append(entry)
    return entries


def write_manifest(entries: list[ManifestEntry], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in entries:
        row = asdict(entry)
        rows.append(json.dumps(row, sort_keys=True))
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return target
