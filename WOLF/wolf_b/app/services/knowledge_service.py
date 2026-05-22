"""
Knowledge Service - RAG-based knowledge base
"""
from typing import List, Dict, Any, Optional
import uuid
import hashlib


class KnowledgeEntry:
    """A single entry in the knowledge base"""

    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.content = content
        self.metadata = metadata or {}
        self.created_at = None
        self.chunks: List[str] = self._chunk_content(content)

    def _chunk_content(self, content: str, chunk_size: int = 500) -> List[str]:
        """Split content into chunks for retrieval"""
        words = content.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            if current_size >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


class KnowledgeService:
    """
    In-memory RAG knowledge base.
    Currently uses simple TF-IDF-like matching.
    Can be extended to use Qdrant, Milvus, or other vector databases.
    """

    def __init__(self):
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._index: Dict[str, List[str]] = {}  # word -> entry_ids

    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the knowledge base.

        Returns:
            The document ID
        """
        entry = KnowledgeEntry(content, metadata)
        entry_id = doc_id or entry.id
        self._entries[entry_id] = entry

        # Simple keyword index
        words = content.lower().split()
        for word in words:
            word = word.strip(".,!?;:()[]{}")
            if len(word) > 3:  # Skip short words
                if word not in self._index:
                    self._index[word] = []
                if entry_id not in self._index[word]:
                    self._index[word].append(entry_id)

        return entry_id

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of matching entries with scores
        """
        query_words = query.lower().split()
        query_words = [w.strip(".,!?;:()[]{}") for w in query_words if len(w) > 3]

        # Score entries by query word matches
        scores: Dict[str, float] = {}
        for word in query_words:
            if word in self._index:
                for entry_id in self._index[word]:
                    scores[entry_id] = scores.get(entry_id, 0) + 1.0

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Apply filters and get top k
        results = []
        for entry_id, score in ranked:
            entry = self._entries[entry_id]

            # Apply metadata filters
            if filters:
                match = True
                for key, value in filters.items():
                    if entry.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # Find best matching chunk
            best_chunk = self._find_best_chunk(entry.chunks, query_words)

            results.append({
                "id": entry_id,
                "content": best_chunk,
                "full_content": entry.content,
                "score": score,
                "metadata": entry.metadata
            })

            if len(results) >= top_k:
                break

        return results

    def _find_best_chunk(self, chunks: List[str], query_words: List[str]) -> str:
        """Find the chunk most relevant to the query"""
        if not chunks:
            return ""

        best_chunk = chunks[0]
        best_score = 0

        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for word in query_words if word in chunk_lower)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        return best_chunk

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry from the knowledge base"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            # Clean up index
            for word, entry_ids in self._index.items():
                if entry_id in entry_ids:
                    entry_ids.remove(entry_id)
            return True
        return False

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entry by ID"""
        if entry_id not in self._entries:
            return None
        entry = self._entries[entry_id]
        return {
            "id": entry_id,
            "content": entry.content,
            "metadata": entry.metadata
        }

    def list_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all entries"""
        return [
            {
                "id": entry_id,
                "content": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content,
                "metadata": entry.metadata
            }
            for entry_id, entry in list(self._entries.items())[:limit]
        ]

    def clear(self) -> None:
        """Clear all entries"""
        self._entries.clear()
        self._index.clear()


# Singleton instance
knowledge_service = KnowledgeService()


# Initialize with some default knowledge
async def init_default_knowledge():
    """Initialize with project documentation"""
    knowledge_service.add_document(
        content="WOLF is an AI research team collaboration platform. "
                "It simulates a real research team with multiple specialized AI agents. "
                "The platform supports task management, agent communication, and knowledge sharing.",
        metadata={"source": "project_docs", "type": "overview"}
    )
