"""
Register RAG + Agentic RAG tools into the WOLF Tool registry
Exposes 7 Agent Tools:
  - rag_search     → Hybrid (vector + BM25 + graph) semantic search
  - rag_ingest     → File/directory ingestion with auto KG building
  - rag_status     → Full RAG status (vector + graph + error book)
  - rag_graph      → Knowledge graph query & traversal
  - rag_error_book → Error book: view stats, patterns, apply corrections
  - rag_correct    → Auto-correct a query using learned corrections
  - rag_build_graph → Explicitly build knowledge graph from indexed docs
"""
from .retriever import Retriever
from .hybrid_retriever import HybridRetriever, get_hybrid_retriever
from .ingest import IngestPipeline
from .store import get_vector_store
from .kg_builder import get_kg_builder
from .error_book import get_error_book


def register_vector_tools():
    """Register all RAG + Agentic RAG tools"""
    retriever = Retriever()
    hybrid = get_hybrid_retriever()
    pipeline = IngestPipeline()
    kg_builder = get_kg_builder()
    error_book = get_error_book()

    # ---- Core RAG Tools ----

    def _rag_search(query: str, top_k: int = 5, collection: str = None,
                    use_hybrid: bool = True, use_graph: bool = True) -> dict:
        """Semantic search with optional hybrid retrieval (vector + BM25 + graph)."""
        if use_hybrid:
            docs = hybrid.retrieve(query, top_k=top_k, collection=collection, use_graph=use_graph)
            if not docs:
                return {"results": [], "method": "hybrid", "message": "No results found"}
            return {
                "results": [
                    {"source": d.get("metadata", {}).get("source", "?"),
                     "score": d.get("rrf_score", d.get("score", 0)),
                     "method": "+".join(d.get("sources", ["vector"])) if isinstance(d.get("sources"), list) else "vector",
                     "content": d.get("text", d.get("content", ""))[:500]}
                    for d in docs
                ],
                "method": "hybrid" if use_graph else "vector+bm25",
                "context": hybrid.retrieve_as_context(query, top_k=top_k, collection=collection, use_graph=use_graph)
            }

        docs = retriever.retrieve(query, top_k=top_k, collection=collection)
        if not docs:
            # Record error for self-improvement
            error_book.record_error(query, "no_results", "rag_search (vector-only)")
            return {"results": [], "method": "vector", "message": "No results found"}
        return {
            "results": [
                {"source": d["metadata"].get("source", "?"),
                 "score": d["score"], "content": d["text"][:500]}
                for d in docs
            ],
            "method": "vector",
            "context": retriever.retrieve_as_context(query, top_k=top_k, collection=collection)
        }

    def _rag_ingest(path: str, collection: str = None,
                    build_graph: bool = True, extensions: list = None) -> dict:
        """Ingest files/directories, optionally building a knowledge graph."""
        import os
        if os.path.isfile(path):
            count = pipeline.ingest_file(path, collection=collection)
        elif os.path.isdir(path):
            count = pipeline.ingest_directory(path, collection=collection, extensions=extensions)
        else:
            return {"error": f"Path not found: {path}", "count": 0}

        kg_count = 0
        if build_graph and count > 0:
            try:
                store = get_vector_store()
                docs = store.get_all(collection=collection, limit=min(count, 200))
                if docs:
                    result = kg_builder.build_from_documents(docs)
                    kg_count = result.get("triples_extracted", 0)
                    kg_builder.save()
                    print(f"[RAG] KG built: {kg_count} triples from {len(docs)} docs")
                else:
                    print(f"[RAG] KG build skipped: no docs retrieved from collection")
            except Exception as e:
                print(f"[RAG] KG build error: {e}")

        return {
            "message": f"Ingested {count} chunks into vector store" +
                       (f", extracted {kg_count} knowledge graph triples" if kg_count else ""),
            "chunks": count,
            "kg_triples": kg_count
        }

    def _rag_status(collection: str = None) -> dict:
        """Full RAG system status: vector store + knowledge graph + error book"""
        store = get_vector_store()
        collections = store.list_collections()
        details = {c: store.count(collection=c) for c in collections}
        kg_status = kg_builder.summary
        eb_stats = error_book.stats

        return {
            "vector_store": {
                "total_documents": sum(details.values()),
                "collections": details
            },
            "knowledge_graph": kg_status,
            "error_book": eb_stats,
            "hybrid_retriever": hybrid.status
        }

    # ---- Agentic RAG Tools ----

    def _rag_graph(entity: str, max_hops: int = 2, relation_filter: str = None) -> dict:
        """Query the knowledge graph: find entities related to the given entity."""
        relations = kg_builder.query(entity, max_hops=max_hops)
        if relation_filter:
            relations = [r for r in relations if relation_filter.lower() in r.get("relation", "").lower()]

        if not relations:
            return {"entity": entity, "results": [], "message": f"No relations found for '{entity}'. Try building the graph first with rag_ingest."}

        return {
            "entity": entity,
            "results": [
                {"target": r.get("target", "?"),
                 "relation": r.get("relation", "?"),
                 "hop": r.get("hop", 0),
                 "path": " → ".join(r.get("path", []))}
                for r in relations[:20]
            ],
            "total": len(relations)
        }

    def _rag_error_book(action: str = "stats", query_text: str = None,
                        term: str = None, synonym: str = None) -> dict:
        """Error Book management: view stats, recent errors, patterns, apply corrections."""
        if action == "stats":
            return {"action": "stats", **error_book.stats}
        elif action == "recent":
            return {"action": "recent", "errors": error_book.get_recent_errors(20)}
        elif action == "patterns":
            patterns = error_book.get_recurring_patterns(min_frequency=2)
            return {"action": "patterns", "patterns": patterns}
        elif action == "correct" and query_text:
            corrected = error_book.correct_query(query_text)
            return {"action": "correct", "original": query_text, "corrected": corrected}
        elif action == "synonym" and term and synonym:
            error_book.add_synonym(term, synonym)
            return {"action": "synonym", "term": term, "synonym_added": synonym}
        return {"action": action, "error": "Unknown action or missing parameters"}

    def _rag_correct(query: str) -> dict:
        """Auto-correct a search query using learned error patterns."""
        corrected = error_book.correct_query(query)
        if corrected == query:
            return {"original": query, "corrected": query, "changed": False,
                    "message": "No corrections needed"}
        # Record that we attempted a fix
        error_book.record_error(query, "auto_corrected", f"Corrected to: {corrected}", attempt_auto_fix=False)
        return {"original": query, "corrected": corrected, "changed": True}

    def _rag_build_graph(source_filter: str = None, collection: str = None) -> dict:
        """Build knowledge graph from already-indexed documents."""
        store = get_vector_store()
        count = store.count(collection=collection)
        if count == 0:
            return {"error": "No documents indexed. Use rag_ingest first.", "triples": 0}

        docs = store.get_all(collection=collection, limit=min(count, 200))
        if not docs:
            return {"error": "Failed to retrieve documents from store.", "triples": 0}

        result = kg_builder.build_from_documents(docs)
        kg_builder.save()
        return {"message": f"Graph built: {result['triples_extracted']} triples from {len(docs)} docs",
                **result}

    # Register all tools
    try:
        from tools.registry import tool_registry
        from skills.tool import ToolDef

        tool_registry.register(ToolDef(
            name="rag_search",
            description="Semantic search with hybrid retrieval (vector + BM25 + knowledge graph). Use natural language to find code/docs by meaning, not just keywords.",
            function=_rag_search
        ))
        tool_registry.register(ToolDef(
            name="rag_ingest",
            description="Import files/directories into RAG vector store and auto-build knowledge graph from content.",
            function=_rag_ingest
        ))
        tool_registry.register(ToolDef(
            name="rag_status",
            description="Full RAG system status: vector store documents, knowledge graph nodes/edges, error book stats.",
            function=_rag_status
        ))
        tool_registry.register(ToolDef(
            name="rag_graph",
            description="Query the knowledge graph: find entities related to a given entity via multi-hop traversal. Use for understanding code dependencies and relationships.",
            function=_rag_graph
        ))
        tool_registry.register(ToolDef(
            name="rag_error_book",
            description="Error Book: view retrieval error stats, recurring patterns, or apply auto-corrections. Use 'stats', 'recent', or 'patterns' actions.",
            function=_rag_error_book
        ))
        tool_registry.register(ToolDef(
            name="rag_correct",
            description="Auto-correct a search query using learned error patterns from the Error Book.",
            function=_rag_correct
        ))
        tool_registry.register(ToolDef(
            name="rag_build_graph",
            description="Build knowledge graph from already-indexed documents (extracts entity-relation triples).",
            function=_rag_build_graph
        ))
    except ImportError:
        pass
