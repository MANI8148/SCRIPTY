"""
Retrieval Evaluator — embeds corpus, indexes with FAISS (optional),
runs 500 benchmark queries, computes per-query and aggregate metrics.
Uses sklearn TF-IDF vectorizer (no torch dependency required).
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from data_pipeline.retrieval.metrics import RetrievalMetrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class RetrievalEvaluator:
    def __init__(self, corpus_path: str, queries_path: str,
                 output_dir: str = "reports/corpus_audit"):
        self.corpus_path = Path(corpus_path)
        self.queries_path = Path(queries_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vectorizer = None
        self.corpus_tfidf = None
        self.corpus: List[dict] = []
        self.corpus_map: Dict[str, dict] = {}
        self.queries: List[dict] = []
        self._load()

    def _load(self):
        if self.corpus_path.exists():
            with open(self.corpus_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        frag = json.loads(line)
                        # Pre-lowercase and pre-compute sets for fast relevance checks
                        frag["_cat_lower"] = frag.get("category", "").lower()
                        frag["_sub_lower"] = frag.get("subcategory", "").lower()
                        frag["_emo_lower"] = frag.get("emotion", "").lower()
                        frag["_tags_set"] = set(
                            t.lower() for t in frag.get("retrieval_tags", [])
                        )
                        self.corpus.append(frag)
                        self.corpus_map[frag["id"]] = frag
        logger.info(f"Loaded {len(self.corpus)} corpus fragments")

        if self.queries_path.exists():
            with open(self.queries_path) as f:
                self.queries = json.load(f)
        logger.info(f"Loaded {len(self.queries)} benchmark queries")

    def _build_index(self):
        if not HAS_NUMPY:
            logger.warning("numpy not available — skipping index building")
            return
        logger.info("Building TF-IDF corpus index...")
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            sublinear_tf=True,
            max_df=0.85,
            min_df=2,
        )
        texts = [f.get("text", "") for f in self.corpus]
        self.corpus_tfidf = self.vectorizer.fit_transform(texts)
        logger.info(f"Built TF-IDF matrix: {self.corpus_tfidf.shape}")

    def search(self, query_text: str, top_k: int = 20) -> List[Tuple[str, float]]:
        if self.vectorizer is None or self.corpus_tfidf is None:
            return []
        q_vec = self.vectorizer.transform([query_text])
        sim = cosine_similarity(q_vec, self.corpus_tfidf).flatten()
        top_idx = sim.argsort()[::-1][:top_k]
        return [(self.corpus[i]["id"], float(sim[i])) for i in top_idx if sim[i] > 0]

    def evaluate_all(self) -> dict:
        self._build_index()
        query_metrics = []
        aggregate = defaultdict(list)

        for i, q in enumerate(self.queries):
            results = self.search(q["query"], top_k=20)
            m = RetrievalMetrics(results, q, self.corpus_map)
            qm = m.all_metrics()
            qm["query"] = q["query"]
            qm["category"] = q.get("category", "")
            qm["subcategory"] = q.get("subcategory", "")
            qm["emotion"] = q.get("emotion", "")
            query_metrics.append(qm)

            for k, v in qm.items():
                if isinstance(v, (int, float)):
                    aggregate[k].append(v)

            if (i + 1) % 100 == 0:
                logger.info(f"Evaluated {i + 1}/{len(self.queries)} queries")

        summary = {
            "total_queries": len(query_metrics),
            "corpus_size": len(self.corpus),
            "aggregate": {},
        }
        if HAS_NUMPY:
            for k, vals in aggregate.items():
                if vals:
                    summary["aggregate"][k] = {
                        "mean": round(float(np.mean(vals)), 4),
                        "median": round(float(np.median(vals)), 4),
                        "min": round(float(np.min(vals)), 4),
                        "max": round(float(np.max(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                    }
        else:
            for k, vals in aggregate.items():
                if vals:
                    sorted_vals = sorted(vals)
                    mid = len(sorted_vals) // 2
                    summary["aggregate"][k] = {
                        "mean": round(sum(vals) / len(vals), 4),
                        "median": round(sorted_vals[mid] if len(sorted_vals) % 2
                                         else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2, 4),
                        "min": round(min(vals), 4),
                        "max": round(max(vals), 4),
                        "std": 0.0,
                    }

        output_path = self.output_dir / "retrieval_metrics.json"
        with open(output_path, "w") as f:
            json.dump({"summary": summary, "per_query": query_metrics}, f, indent=2)
        logger.info(f"Wrote {output_path}")
        return summary

    def generate_report(self):
        summary = self.evaluate_all()
        path = self.output_dir / "retrieval_evaluation_report.md"
        lines = []
        lines.append("# Retrieval Evaluation Report\n")
        lines.append(f"**Corpus Size**: {summary['corpus_size']} fragments\n")
        lines.append(f"**Total Queries**: {summary['total_queries']}\n")
        lines.append("\n## Aggregate Metrics\n")
        lines.append("| Metric | Mean | Median | Min | Max | Std |\n")
        lines.append("|--------|------|--------|-----|-----|-----|\n")
        agg = summary["aggregate"]
        for k in sorted(agg.keys()):
            v = agg[k]
            lines.append(f"| {k} | {v['mean']} | {v['median']} | {v['min']} | {v['max']} | {v['std']} |\n")
        with open(path, "w") as f:
            f.writelines(lines)
        logger.info(f"Wrote {path}")
        return summary


if __name__ == "__main__":
    import sys
    corpus = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    queries = sys.argv[2] if len(sys.argv) > 2 else "data_pipeline/retrieval/benchmark_queries.json"
    output = sys.argv[3] if len(sys.argv) > 3 else "reports/corpus_audit"
    ev = RetrievalEvaluator(corpus, queries, output)
    ev.generate_report()
