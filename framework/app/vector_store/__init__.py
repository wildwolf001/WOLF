"""
WOLF Vector Store — RAG + Agentic RAG 语义检索子系统
Vector search (ChromaDB) + Knowledge Graph (Kuzu/InMemory) + Hybrid RRF + Error Book
"""
from .store import VectorStore, get_vector_store
from .embedder import Embedder, get_embedder
from .splitter import TextSplitter, split_code, split_markdown
from .retriever import Retriever
from .ingest import IngestPipeline
from .hybrid_retriever import HybridRetriever, get_hybrid_retriever, BM25Scorer, GraphRetriever, reciprocal_rank_fusion
from .kg_builder import AutoKGBuilder, get_kg_builder
from .error_book import ErrorBook, get_error_book


def setup_vector_store(embedding_model: str = None):
    """在 main.py lifespan 中调用，初始化向量库 + Embedder + KG + Error Book + 注册 Tools"""
    # 初始化 Embedder
    from .embedder import get_embedder
    get_embedder(model_name=embedding_model)

    # 初始化 VectorStore
    from .store import get_vector_store
    store = get_vector_store()

    # 初始化 Knowledge Graph Builder (load persisted graph if exists)
    from .kg_builder import get_kg_builder
    kg = get_kg_builder()
    try:
        kg.load()
    except Exception:
        pass

    # 初始化 Hybrid Retriever
    from .hybrid_retriever import get_hybrid_retriever
    get_hybrid_retriever()

    # 初始化 Error Book
    from .error_book import get_error_book
    get_error_book()

    # 注册所有 Agent Tools (7 tools: search/ingest/status/graph/error_book/correct/build_graph)
    from .tool import register_vector_tools
    register_vector_tools()

    return store


__all__ = [
    "VectorStore", "get_vector_store",
    "Embedder", "get_embedder",
    "TextSplitter", "split_code", "split_markdown",
    "Retriever",
    "IngestPipeline",
    "HybridRetriever", "get_hybrid_retriever", "BM25Scorer", "GraphRetriever", "reciprocal_rank_fusion",
    "AutoKGBuilder", "get_kg_builder",
    "ErrorBook", "get_error_book",
    "setup_vector_store",
]
