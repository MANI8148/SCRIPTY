from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from backend.research.dataset_manifest import ManifestEntry, split_passages, write_manifest


def fetch_text(url: str, timeout: int = 20, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "SCRIPTY research dataset builder"})
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                return soup.get_text("\n")
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
    raise last_error or RuntimeError(f"failed to fetch {url}")


def clean_public_domain_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_entry(source: dict, max_passages: int | None = None) -> ManifestEntry:
    source_id = source["source_id"]
    url = source["url"]
    text = clean_public_domain_text(fetch_text(url))
    passage_metadata = {
        "split": source.get("split", "corpus"),
        "domain": urlparse(url).netloc,
        "region": source.get("region", "global"),
        "period": source.get("period", "unknown"),
        "genre": source.get("genre", "unknown"),
        "source_type": source.get("source_type", "book"),
        "section": source.get("section", "uncategorized"),
    }
    passages = split_passages(source_id, text, metadata=passage_metadata)
    if max_passages is not None:
        passages = passages[:max_passages]
    return ManifestEntry(
        source_id=source_id,
        title=source["title"],
        author=source["author"],
        license=source["license"],
        url=url,
        passages=passages,
        metadata=source.get("metadata", {}),
        source_type=source.get("source_type", "book"),
        period=source.get("period", "unknown"),
        region=source.get("region", "global"),
        language=source.get("language", "en"),
        rights_status=source.get("rights_status", "public_domain"),
        genre=source.get("genre", "unknown"),
    )


def load_sources(raw_sources: list[str] | None, catalog_path: str | None) -> list[dict]:
    sources = []
    if catalog_path:
        catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        if isinstance(catalog, list):
            sources.extend(catalog)
        elif "sections" in catalog:
            for section in catalog["sections"]:
                for source in section.get("sources", []):
                    source = source.copy()
                    source.setdefault("section", section.get("name", "uncategorized"))
                    sources.append(source)
        else:
            sources.extend(catalog.get("sources", []))
    for raw_source in raw_sources or []:
        sources.append(json.loads(raw_source))
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public-domain source text and build SCRIPTY dataset manifest JSONL.")
    parser.add_argument("--source", action="append", help="JSON object with source_id,title,author,license,url[,split]")
    parser.add_argument("--catalog", help="Path to JSON catalog with a sources array")
    parser.add_argument("--output", default="backend/data/dataset_manifest.jsonl")
    parser.add_argument("--max-passages-per-source", type=int, default=None)
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()
    sources = load_sources(args.source, args.catalog)
    if not sources:
        parser.error("provide at least one --source or --catalog")
    entries = []
    failures = []
    for source in sources:
        try:
            entries.append(build_entry(source, max_passages=args.max_passages_per_source))
        except Exception as exc:  # noqa: BLE001
            failure = {"source_id": source.get("source_id", "unknown"), "error": str(exc)}
            failures.append(failure)
            if args.fail_fast:
                raise
    target = write_manifest(entries, args.output)
    print(json.dumps({
        "output": str(Path(target)),
        "entries": len(entries),
        "failures": failures,
        "failure_count": len(failures),
        "passages": sum(len(entry.passages) for entry in entries),
        "regions": sorted({entry.region for entry in entries}),
        "genres": sorted({entry.genre for entry in entries}),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
