"""
Agentic RAG Tool Parameter Definitions
Provides typed parameter schemas for knowledge-graph-enhanced retrieval tools.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class RAGSearchParams(BaseModel):
    """Agentic RAG semantic search parameters"""
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    collection: Optional[str] = Field(default=None, description="Target collection name")
    use_graph: bool = Field(default=True, description="Enable knowledge graph traversal for multi-hop reasoning")
    use_hybrid: bool = Field(default=True, description="Use hybrid retrieval (vector + BM25 + graph) instead of vector-only")


class RAGIngestParams(BaseModel):
    """Agentic RAG document ingestion parameters"""
    path: str = Field(..., description="File or directory path to ingest")
    collection: Optional[str] = Field(default=None, description="Target collection name")
    build_graph: bool = Field(default=True, description="Auto-build knowledge graph from ingested content")
    extensions: Optional[List[str]] = Field(default=None, description="File extensions to include (e.g., ['.py', '.md'])")


class GraphQueryParams(BaseModel):
    """Knowledge graph query parameters"""
    entity: str = Field(..., description="Entity name to start graph traversal from")
    max_hops: int = Field(default=2, ge=1, le=5, description="Maximum graph traversal hops")
    relation_filter: Optional[str] = Field(default=None, description="Filter by relation type (e.g., 'imports', 'depends_on')")


class ErrorBookParams(BaseModel):
    """Error book query parameters"""
    action: str = Field(default="stats", description="Action: stats, recent, patterns, correct, synonym")
    query_text: Optional[str] = Field(default=None, description="Query text (for 'correct' action)")
    term: Optional[str] = Field(default=None, description="Term (for 'synonym' action)")
    synonym: Optional[str] = Field(default=None, description="Synonym to add (for 'synonym' action)")


class RAGStatusParams(BaseModel):
    """Full RAG status parameters (includes graph and error book)"""
    collection: Optional[str] = Field(default=None, description="Target collection name")
