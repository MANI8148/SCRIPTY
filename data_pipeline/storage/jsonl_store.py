import json
import logging
from typing import List, Iterator, TypeVar, Generic
from pathlib import Path

from data_pipeline.schema.fragment import (
    NarrativeFragment, CharacterMemoryFragment,
    ForeshadowingLink, SceneBlueprint,
)


T = TypeVar('T')
logger = logging.getLogger(__name__)


class JsonlStore(Generic[T]):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _serialize(self, item: T) -> str:
        if hasattr(item, 'to_json'):
            return item.to_json()
        return json.dumps(item, ensure_ascii=False)

    def append(self, item: T) -> None:
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(self._serialize(item) + '\n')

    def append_batch(self, items: List[T]) -> None:
        with open(self.file_path, 'a', encoding='utf-8') as f:
            for item in items:
                f.write(self._serialize(item) + '\n')

    def read_all(self) -> List[T]:
        items = []
        if not self.file_path.exists():
            return items
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        items.append(self._from_dict(data))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed JSON line")
        return items

    def count(self) -> int:
        if not self.file_path.exists():
            return 0
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())

    def clear(self) -> None:
        if self.file_path.exists():
            self.file_path.unlink()

    def _from_dict(self, data: dict) -> T:
        return data

    @staticmethod
    def for_fragments(path: str) -> 'JsonlStore[NarrativeFragment]':
        store = JsonlStore[NarrativeFragment](path)
        store._from_dict = lambda d: NarrativeFragment.from_dict(d)
        return store

    @staticmethod
    def for_character_memories(path: str) -> 'JsonlStore[CharacterMemoryFragment]':
        store = JsonlStore[CharacterMemoryFragment](path)
        store._from_dict = lambda d: CharacterMemoryFragment(**d)
        return store

    @staticmethod
    def for_scene_blueprints(path: str) -> 'JsonlStore[SceneBlueprint]':
        store = JsonlStore[SceneBlueprint](path)
        store._from_dict = lambda d: SceneBlueprint(**d)
        return store


class JsonStore:
    @staticmethod
    def save_json(file_path: str, data: object) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_json(file_path: str) -> object:
        path = Path(file_path)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
