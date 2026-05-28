"""
检索器：向量粗筛 → 关键词重排序 → LLM 上下文格式化
"""
from typing import List
from .store import VectorStore, get_vector_store


class Retriever:
    """检索器"""

    def __init__(self, store: VectorStore = None):
        self._store = store or get_vector_store()

    def retrieve(self, query: str, top_k: int = 5,
                 collection: str = None, source_filter: str = None) -> List[dict]:
        """检索 + 关键词重排序"""
        where = {"source": source_filter} if source_filter else None
        candidates = self._store.query(
            query_text=query, n_results=top_k * 2,
            collection=collection, where=where
        )
        if not candidates:
            return []

        # 关键词重叠加权 (简化 BM25)
        query_words = set(query.lower().split())
        for doc in candidates:
            text_words = set(doc["text"].lower().split())
            overlap = len(query_words & text_words)
            doc["score"] = round(doc["score"] * 0.7 + (overlap / max(len(query_words), 1)) * 0.3, 4)

        return sorted(candidates, key=lambda d: d["score"], reverse=True)[:top_k]

    def retrieve_as_context(self, query: str, top_k: int = 5,
                            collection: str = None) -> str:
        """检索结果 → LLM Prompt 可用的上下文字符串"""
        docs = self.retrieve(query, top_k=top_k, collection=collection)
        if not docs:
            return ""

        parts = []
        for i, doc in enumerate(docs):
            source = doc["metadata"].get("source", "unknown")
            parts.append(
                f"【参考文档 {i+1}】来源: {source} (相关度: {doc['score']:.2f})\n"
                f"{doc['text']}\n"
            )
        return "\n".join(parts)
