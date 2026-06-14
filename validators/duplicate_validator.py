import re
from typing import List, Dict, Any, Tuple, Set
from difflib import SequenceMatcher


NEAR_DUPLICATE_THRESHOLD = 0.85


class DuplicateValidator:
    def validate(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        passed: List[Tuple[int, str]] = []
        failed: List[Tuple[int, str]] = []

        fragments: List[str] = []
        for item in items:
            text = item.get("text", "")
            fragments.append(text)

        normalized_texts: List[str] = []
        for frag in fragments:
            norm = self._normalize(frag)
            normalized_texts.append(norm)

        total_fragments = len(normalized_texts)
        exact_duplicates: Set[int] = set()
        near_duplicate_groups: List[Set[int]] = []

        for i in range(total_fragments):
            for j in range(i + 1, total_fragments):
                if normalized_texts[i] == normalized_texts[j]:
                    exact_duplicates.add(j)

        seen_near: Set[int] = set()
        for i in range(total_fragments):
            if i in seen_near:
                continue
            group: Set[int] = {i}
            for j in range(i + 1, total_fragments):
                if j in seen_near:
                    continue
                sim = SequenceMatcher(None, normalized_texts[i], normalized_texts[j]).ratio()
                if sim >= NEAR_DUPLICATE_THRESHOLD and normalized_texts[i] != normalized_texts[j]:
                    group.add(j)
            if len(group) > 1:
                near_duplicate_groups.append(group)
                seen_near.update(group)

        for idx in exact_duplicates:
            failed.append((idx, f"Exact duplicate of earlier item"))

        marked = set(exact_duplicates)
        for group in near_duplicate_groups:
            rep = min(group)
            for idx in group:
                if idx == rep:
                    continue
                if idx not in marked:
                    failed.append((idx, f"Near-duplicate of item {rep}"))
                    marked.add(idx)

        for idx in range(total_fragments):
            if idx not in exact_duplicates and idx not in marked:
                passed.append((idx, "Unique fragment"))

        dedup_count = len(exact_duplicates) + sum(len(g) - 1 for g in near_duplicate_groups)
        unique_after_merge = total_fragments - dedup_count

        duplicate_count = total_fragments - unique_after_merge
        duplicate_rate = duplicate_count / total_fragments if total_fragments > 0 else 0.0
        duplicate_reduction_rate = 1.0 - (unique_after_merge / total_fragments) if total_fragments > 0 else 0.0
        merge_efficiency = len(exact_duplicates) + len(near_duplicate_groups)

        return {
            "passed": passed,
            "failed": failed,
            "metrics": {
                "duplicate_rate": duplicate_rate,
                "duplicate_reduction_rate": duplicate_reduction_rate,
                "post_dedup_rate": 0.0,
                "merge_efficiency": float(merge_efficiency),
            },
        }

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r'\s+', ' ', text)
        return text
