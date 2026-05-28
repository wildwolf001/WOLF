"""
WOLF Vector Store Module
Embedding 模型封装 — 文本 → 向量
"""
from typing import List
import hashlib
import numpy as np

class Embedder:
    """
    Embedding 模型封装，默认 BAAI/bge-small-zh-v1.5 (512维, 中英双语)
    支持后端: sentence-transformers (本地) / openai (API)
    """

    def __init__(self, backend: str = "sentence-transformers", model_name: str = None):
        self.backend = backend
        self._model = None

        if backend == "sentence-transformers":
            model_name = model_name or "BAAI/bge-small-zh-v1.5"
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(model_name)
            except ImportError:
                print("[vector_store] sentence-transformers 未安装，使用伪向量模式")
        elif backend == "openai":
            self._model_name = model_name or "text-embedding-3-small"

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量编码 → [[float, ...], ...]"""
        if self.backend == "sentence-transformers" and self._model:
            return self._model.encode(texts, normalize_embeddings=True).tolist()
        elif self.backend == "openai":
            import openai
            resp = openai.embeddings.create(model=self._model_name, input=texts)
            return [d.embedding for d in resp.data]
        else:
            return self._fallback_embed(texts)

    def embed_query(self, text: str) -> List[float]:
        """单条查询 → [float, ...]"""
        return self.embed([text])[0]

    def _fallback_embed(self, texts: List[str]) -> List[List[float]]:
        """无模型时伪向量回退 (仅测试用)"""
        dim = 384
        vectors = []
        for t in texts:
            seed = int(hashlib.md5(t.encode()).hexdigest(), 16) % (2**31)
            rng = np.random.RandomState(seed)
            vectors.append(rng.randn(dim).tolist())
        return vectors


_embedder: Embedder = None

def get_embedder(backend: str = None, model_name: str = None) -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder(backend=backend or "sentence-transformers", model_name=model_name)
    return _embedder
