from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class LLMAdapter:
    def __init__(self, enabled: bool = False, endpoint: str = "http://127.0.0.1:11434/api/generate", model: str = "llama3", fallback: Any | None = None) -> None:
        self.enabled = enabled
        self.endpoint = endpoint
        self.model = model
        self.fallback = fallback

    def build_prompt(self, scene_type: str, context: dict, max_tokens: int = 512) -> str:
        parts = [
            f"Write a {scene_type} historical fiction scene.",
            f"Location: {context.get('location')}",
            f"Year: {context.get('year')}",
            f"Genre: {context.get('genre')}",
            f"Characters: {context.get('protagonist')} and {context.get('antagonist')}",
            f"Use no more than {max_tokens} tokens.",
        ]
        prompt = "\n".join(str(part) for part in parts if part)
        return " ".join(prompt.split()[:max_tokens])

    def build_scene(self, scene_type: Any, context: dict, scene_num: int, max_tokens: int = 512) -> str:
        if not self.enabled:
            return self.fallback.build_scene(scene_type, context, scene_num) if self.fallback else ""
        prompt = self.build_prompt(getattr(scene_type, "value", str(scene_type)), context, max_tokens)
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
        try:
            request = urllib.request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
                return str(data.get("response", "")).strip()
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            logger.warning("llm_adapter_fallback", extra={"error": str(exc)})
            return self.fallback.build_scene(scene_type, context, scene_num) if self.fallback else ""
