"""
Hybrid Retriever — Vector + BM25 + Graph traversal → RRF fusion
Three retrieval paths fused with Reciprocal Rank Fusion for optimal recall.
"""
import os
import re
import math
from typing import List, Dict, Optional
from .store import get_vector_store
from .kg_builder import get_kg_builder


# ---------- BM25 implementation (lightweight, no external deps) ----------

class BM25Scorer:
    """Lightweight BM25 keyword scorer with IDF weighting"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._doc_freq: Dict[str, int] = {}
        self._doc_count = 0
        self._avg_doc_len = 0
        self._doc_lengths: List[int] = []

    def index(self, documents: List[Dict]):
        """Index documents for BM25 scoring"""
        self._doc_count = len(documents)
        self._doc_freq = {}
        self._doc_lengths = []
        total_len = 0

        for doc in documents:
            text = doc.get("text", doc.get("content", ""))
            tokens = self._tokenize(text)
            self._doc_lengths.append(len(tokens))
            total_len += len(tokens)

            seen = set()
            for token in tokens:
                if token not in seen:
                    self._doc_freq[token] = self._doc_freq.get(token, 0) + 1
                    seen.add(token)

        self._avg_doc_len = total_len / max(self._doc_count, 1)

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenizer"""
        return re.findall(r'[a-zA-Z_]\w*|[^\x00-\x7F]+', text.lower())

    def _idf(self, term: str) -> float:
        df = self._doc_freq.get(term, 0)
        return math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1)

    def score(self, query: str, doc_idx: int) -> float:
        """BM25 score for a single document"""
        query_tokens = self._tokenize(query)
        if doc_idx >= self._doc_count:
            return 0.0

        doc_len = self._doc_lengths[doc_idx]
        score = 0.0

        for token in query_tokens:
            idf = self._idf(token)
            # Term frequency in this document (approximate from doc_freq)
            tf = self._doc_freq.get(token, 0) / max(self._doc_count, 1)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self._avg_doc_len, 1))
            score += idf * numerator / max(denominator, 0.001)

        return round(score, 4)

    def search(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Dict]:
        """Search documents with BM25 scores"""
        scored = []
        for i, doc in enumerate(documents):
            s = self.score(query, i)
            if s > 0:
                scored.append({**doc, "bm25_score": s, "doc_idx": i})

        return sorted(scored, key=lambda d: d["bm25_score"], reverse=True)[:top_k]


# ---------- RRF Fusion ----------

def reciprocal_rank_fusion(
    result_sets: List[List[Dict]],
    score_keys: List[str],
    k: int = 60
) -> List[Dict]:
    """
    Reciprocal Rank Fusion — merge multiple ranked result lists.
    Each result set is sorted by its score (descending).
    score_keys: the key name for the score in each result set.
    """
    fused: Dict[str, Dict] = {}  # doc_id → merged_doc

    for result_set, score_key in zip(result_sets, score_keys):
        for rank, doc in enumerate(result_set):
            doc_id = doc.get("metadata", {}).get("source", "") + ":" + doc.get("text", "")[:50]
            rrf_score = 1.0 / (k + rank + 1)

            if doc_id not in fused:
                fused[doc_id] = {**doc, "rrf_score": rrf_score, "sources": [score_key]}
            else:
                fused[doc_id]["rrf_score"] += rrf_score
                if score_key not in fused[doc_id]["sources"]:
                    fused[doc_id]["sources"].append(score_key)

    return sorted(fused.values(), key=lambda d: d["rrf_score"], reverse=True)


# ---------- Graph Traversal Retriever ----------

class GraphRetriever:
    """Retrieve documents via knowledge graph traversal"""

    def __init__(self):
        self._kg = get_kg_builder()

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Find entities in query, traverse graph for related documents"""
        # Extract potential entities from query (capitalized words, known terms)
        words = re.findall(r'[A-Z][a-z]+|[a-z]+(?:_[a-z]+)+|[A-Z]{2,}', query)
        results = []

        for word in words[:3]:  # Query up to 3 entities
            relations = self._kg.query(word, max_hops=2)
            for rel in relations:
                results.append({
                    "text": f"Graph: {' → '.join(rel.get('path', [rel.get('relation', '')]))}",
                    "metadata": {
                        "source": "knowledge_graph",
                        "source_entity": word,
                        "relation": rel.get("relation", ""),
                        "hop": rel.get("hop", 0)
                    },
                    "graph_score": 1.0 / (rel.get("hop", 1) + 1),
                    "path": rel.get("path", [])
                })

        return sorted(results, key=lambda d: d["graph_score"], reverse=True)[:top_k]


# ---------- Hybrid Retriever ----------

class HybridRetriever:
    """
    Three-way hybrid retriever:
    1. Vector (ChromaDB semantic)
    2. BM25 (keyword sparse)
    3. Graph (knowledge graph traversal)

    Fused with RRF for final ranking.
    """

    def __init__(self):
        self._vector_store = get_vector_store()
        self._bm25 = BM25Scorer()
        self._graph = GraphRetriever()
        self._kg_builder = get_kg_builder()

    def retrieve(self, query: str, top_k: int = 5,
                 collection: str = None, use_graph: bool = True) -> List[Dict]:
        """Three-way retrieval + RRF fusion"""

        # --- Path 1: Vector retrieval ---
        vector_results = self._vector_store.query(
            query_text=query, n_results=top_k * 2, collection=collection
        )

        # --- Path 2: BM25 keyword ---
        # Use the same documents for BM25 scoring
        self._bm25.index(vector_results if vector_results else [])
        bm25_results = self._bm25.search(query, vector_results if vector_results else [], top_k)

        # --- Path 3: Graph traversal ---
        graph_results = []
        if use_graph and self._kg_builder.graph.node_count > 0:
            graph_results = self._graph.retrieve(query, top_k)

        # --- RRF Fusion ---
        all_results = reciprocal_rank_fusion(
            result_sets=[vector_results, bm25_results, graph_results],
            score_keys=["score", "bm25_score", "graph_score"]
        )

        return all_results[:top_k]

    def retrieve_as_context(self, query: str, top_k: int = 5,
                            collection: str = None, use_graph: bool = True) -> str:
        """Retrieve and format as LLM context with source annotations"""
        docs = self.retrieve(query, top_k=top_k, collection=collection, use_graph=use_graph)
        if not docs:
            return ""

        parts = []
        for i, doc in enumerate(docs):
            source = doc.get("metadata", {}).get("source", "unknown")
            sources = doc.get("sources", ["vector"])
            rrf = doc.get("rrf_score", 0)
            method = "+".join(sources) if isinstance(sources, list) else sources

            parts.append(
                f"【参考文档 {i+1}】来源: {source} | 检索: {method} | RRF: {rrf:.3f}\n"
                f"{doc.get('text', doc.get('content', ''))}\n"
            )

        return "\n".join(parts)

    @property
    def status(self) -> dict:
        return {
            "vector_docs": self._vector_store.count(),
            "graph_nodes": self._kg_builder.graph.node_count,
            "graph_edges": self._kg_builder.graph.edge_count,
        }


_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
