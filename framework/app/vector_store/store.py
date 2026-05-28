"""
ChromaDB 向量存储 CRUD 封装
"""
import os
import uuid
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from .embedder import get_embedder


class VectorStore:
    """ChromaDB 持久化向量存储"""

    def __init__(self, persist_path: str = None, collection_name: str = "wolf_knowledge"):
        persist_path = persist_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "vector_db"
        )
        os.makedirs(persist_path, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection_name = collection_name
        self._embedder = get_embedder()

    def get_or_create_collection(self, name: str = None):
        return self._client.get_or_create_collection(name=name or self.collection_name)

    def list_collections(self) -> List[str]:
        return [c.name for c in self._client.list_collections()]

    def add(self, texts: List[str], metadatas: List[dict] = None,
            ids: List[str] = None, collection: str = None) -> List[str]:
        """写入文档块 → 返回 ID 列表"""
        col = self.get_or_create_collection(collection)
        embeddings = self._embedder.embed(texts)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        col.add(embeddings=embeddings, documents=texts,
                metadatas=metadatas or [{}] * len(texts), ids=ids)
        return ids

    def query(self, query_text: str, n_results: int = 5,
              collection: str = None, where: dict = None) -> List[dict]:
        """语义检索 → [{"text","metadata","score"}]"""
        col = self.get_or_create_collection(collection)
        query_embedding = self._embedder.embed_query(query_text)
        results = col.query(
            query_embeddings=[query_embedding], n_results=n_results,
            where=where, include=["documents", "metadatas", "distances"]
        )
        docs = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                dist = (results.get("distances") or [[0]])[0][i]
                docs.append({
                    "text": doc,
                    "metadata": (results.get("metadatas") or [{}])[0][i],
                    "score": round(1.0 / (1.0 + dist), 4)
                })
        return docs

    def remove_by_source(self, source_path: str, collection: str = None):
        col = self.get_or_create_collection(collection)
        results = col.get(where={"source": source_path})
        if results["ids"]:
            col.delete(ids=results["ids"])

    def delete_collection(self, name: str):
        try:
            self._client.delete_collection(name=name)
            return True
        except Exception:
            return False

    def get_all(self, collection: str = None, limit: int = 200) -> List[dict]:
        """获取集合中的所有文档（用于 KG 构建等批量操作）"""
        col = self.get_or_create_collection(collection)
        total = col.count()
        if total == 0:
            return []
        limit = min(limit, total)
        results = col.get(limit=limit, include=["documents", "metadatas"])
        docs = []
        if results.get("documents"):
            for i, doc in enumerate(results["documents"]):
                docs.append({
                    "text": doc,
                    "metadata": (results.get("metadatas") or [{}])[i] if i < len(results.get("metadatas") or []) else {},
                    "score": 1.0
                })
        return docs

    def count(self, collection: str = None) -> int:
        return self.get_or_create_collection(collection).count()


_store: Optional[VectorStore] = None

def get_vector_store(path: str = None) -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(persist_path=path)
    return _store
