"""记忆-向量库同步桥 — 写入记忆时自动同步到 ChromaDB"""
import os
from typing import Optional

def sync_memory_on_write(memory_data: dict):
    """写入记忆后调用此 hook，同步到向量库"""
    try:
        from ..vector_store.store import get_vector_store
        store = get_vector_store()
        content = memory_data.get("content", "")
        if not content:
            return
        store.add(
            texts=[content],
            metadatas=[{
                "source": f"memory:{memory_data.get('id', '?')}",
                "memory_type": memory_data.get("memory_type", "general"),
                "source_file": "memory_sync"
            }],
            collection="wolf_memories"
        )
    except ImportError:
        pass
    except Exception as e:
        print(f"[memory.vector_sync] sync failed: {e}")

def semantic_search_memories(query: str, memory_type: str = None, top_k: int = 5) -> list:
    """语义搜索记忆"""
    try:
        from ..vector_store.store import get_vector_store
        store = get_vector_store()
        where = {"memory_type": memory_type} if memory_type else None
        return store.query(query_text=query, n_results=top_k, collection="wolf_memories", where=where)
    except ImportError:
        return []
    except Exception:
        return []
