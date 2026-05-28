"""
Knowledge Graph Builder — LLM-driven entity-relation extraction → graph storage
Powered by Kuzu (embedded graph DB) with in-memory JSON fallback.
"""
import os
import json
import time
from typing import List, Dict, Tuple, Optional

# Try Kuzu first, fall back to in-memory graph
_KUZU_AVAILABLE = False
try:
    import kuzu
    _KUZU_AVAILABLE = True
except ImportError:
    pass


class InMemoryGraph:
    """Simple in-memory directed graph — fallback when Kuzu is not available"""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}       # node_id → {label, properties}
        self.edges: List[Dict] = []             # [{source, target, relation, properties}]

    def add_node(self, node_id: str, label: str, properties: dict = None):
        self.nodes[node_id] = {"label": label, "properties": properties or {}}

    def add_edge(self, source: str, target: str, relation: str, properties: dict = None):
        self.edges.append({
            "source": source, "target": target, "relation": relation,
            "properties": properties or {}
        })

    def query_relations(self, entity: str, max_hops: int = 2) -> List[Dict]:
        """BFS traversal from entity up to max_hops"""
        visited = set()
        results = []
        queue = [(entity, 0, None)]

        while queue:
            current, hop, path = queue.pop(0)
            if current in visited or hop > max_hops:
                continue
            visited.add(current)

            for edge in self.edges:
                if edge["source"] == current:
                    results.append({
                        "source": current, "target": edge["target"],
                        "relation": edge["relation"], "hop": hop + 1,
                        "path": (path or []) + [f"{current}-[{edge['relation']}]->{edge['target']}"]
                    })
                    queue.append((edge["target"], hop + 1, results[-1]["path"]))
                elif edge["target"] == current:
                    results.append({
                        "source": edge["source"], "target": current,
                        "relation": edge["relation"], "hop": hop + 1,
                        "path": (path or []) + [f"{edge['source']}-[{edge['relation']}]->{current}"]
                    })
        return results

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def summary(self) -> dict:
        return {"nodes": self.node_count, "edges": self.edge_count,
                "labels": list(set(n["label"] for n in self.nodes.values()))}


class KuzuGraph:
    """Kuzu embedded graph database adapter"""

    def __init__(self, db_path: str):
        parent = os.path.dirname(db_path)
        os.makedirs(parent, exist_ok=True)
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._init_schema()

    def _init_schema(self):
        try:
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Entity(id STRING, label STRING, type STRING, PRIMARY KEY(id))")
        except Exception:
            pass
        try:
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS RELATED(FROM Entity TO Entity, relation STRING, weight DOUBLE)")
        except Exception:
            pass

    def add_entity(self, entity_id: str, label: str, etype: str = "concept"):
        try:
            self.conn.execute(f"MERGE (e:Entity {{id: '{entity_id}'}}) SET e.label = '{label}', e.type = '{etype}'")
        except Exception:
            pass

    def add_relation(self, source: str, target: str, relation: str, weight: float = 1.0):
        try:
            self.conn.execute(
                f"MATCH (a:Entity {{id: '{source}'}}), (b:Entity {{id: '{target}'}}) "
                f"MERGE (a)-[:RELATED {{relation: '{relation}', weight: {weight}}}]->(b)"
            )
        except Exception:
            pass

    def traverse(self, entity_id: str, max_hops: int = 2) -> List[Dict]:
        try:
            result = self.conn.execute(
                f"MATCH (a:Entity {{id: '{entity_id}'}})-[r:RELATED*1..{max_hops}]-(b:Entity) "
                f"RETURN b.id, b.label, relationships(r)"
            )
            rows = []
            while result.has_next():
                row = result.get_next()
                rows.append({"id": row[0], "label": row[1]})
            return rows
        except Exception:
            return []

    @property
    def node_count(self) -> int:
        try:
            r = self.conn.execute("MATCH (e:Entity) RETURN count(e)")
            return r.get_next()[0] if r.has_next() else 0
        except Exception:
            return 0


class AutoKGBuilder:
    """
    Auto Knowledge Graph Builder
    LLM extracts (entity, relation, entity) triples from text → graph write
    """

    def __init__(self, db_path: str = None):
        db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "knowledge_graph"
        )
        if _KUZU_AVAILABLE:
            kuzu_path = os.path.join(db_path, "kuzu_db")
            self.graph = KuzuGraph(kuzu_path)
        else:
            self.graph = InMemoryGraph()

        self._triple_cache: set = set()  # dedup triples

    def extract_triples_from_text(self, text: str, llm_client=None) -> List[Tuple[str, str, str]]:
        """
        Extract (entity, relation, entity) triples from text.
        If llm_client is provided, uses LLM; otherwise uses heuristic extraction.
        """
        if llm_client:
            return self._llm_extract(text, llm_client)
        return self._heuristic_extract(text)

    def _heuristic_extract(self, text: str) -> List[Tuple[str, str, str]]:
        """Heuristic triple extraction: find capitalized entities and their relationships"""
        import re
        triples = []

        # Pattern: "A uses B", "A depends on B", "A calls B", "A imports B"
        patterns = [
            (r'(\w+)\s+(?:is|are)\s+(?:a|an)\s+(\w+)', 'is_a'),
            (r'(\w+)\s+(?:uses?|utilizes?)\s+(\w+)', 'uses'),
            (r'(\w+)\s+(?:depends?\s+on|requires?)\s+(\w+)', 'depends_on'),
            (r'(\w+)\s+(?:calls?|invokes?)\s+(\w+)', 'calls'),
            (r'(\w+)\s+(?:imports?|includes?)\s+(\w+)', 'imports'),
            (r'(\w+)\s+(?:extends?|inherits?\s+(?:from\s+)?)\s+(\w+)', 'extends'),
            (r'(\w+)\s+(?:returns?|produces?|outputs?)\s+(\w+)', 'produces'),
            (r'(\w+)\s+(?:handles?|processes?|manages?)\s+(\w+)', 'handles'),
        ]

        for pattern, relation in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1)
                target = match.group(2)
                key = (source.lower(), relation, target.lower())
                if key not in self._triple_cache and len(source) > 1 and len(target) > 1:
                    self._triple_cache.add(key)
                    triples.append((source, relation, target))

        return triples

    def _llm_extract(self, text: str, llm_client) -> List[Tuple[str, str, str]]:
        """Use LLM to extract knowledge triples"""
        prompt = (
            "Extract knowledge triples from the following text. "
            "Each triple should be in the format: (entity1, relation, entity2)\n\n"
            "Relations should be simple verbs/phrases: uses, depends_on, calls, imports, "
            "extends, implements, handles, contains, returns, configures, defines, connects_to\n\n"
            f"Text:\n{text[:3000]}\n\n"
            "Output ONLY the triples, one per line, in JSON format:\n"
            '["entity1", "relation", "entity2"]'
        )
        try:
            import asyncio
            response = asyncio.get_event_loop().run_until_complete(
                llm_client.complete(prompt)
            )
            import re
            triples = []
            for line in response.split('\n'):
                match = re.search(r'\["([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\]', line.strip())
                if match:
                    s, r, t = match.group(1), match.group(2), match.group(3)
                    key = (s.lower(), r, t.lower())
                    if key not in self._triple_cache:
                        self._triple_cache.add(key)
                        triples.append((s, r, t))
            return triples
        except Exception:
            return self._heuristic_extract(text)

    def build_from_text(self, text: str, source: str = "", llm_client=None) -> int:
        """Extract triples from text and build graph. Returns triple count."""
        triples = self.extract_triples_from_text(text, llm_client)
        for source_entity, relation, target_entity in triples:
            self.graph.add_node(source_entity, source_entity, "concept")
            self.graph.add_node(target_entity, target_entity, "concept")
            self.graph.add_edge(source_entity, target_entity, relation)

        return len(triples)

    def build_from_documents(self, documents: List[Dict], llm_client=None) -> Dict:
        """Batch build graph from retrieved documents. Returns stats."""
        total_triples = 0
        for doc in documents:
            text = doc.get("text", doc.get("content", ""))
            source = doc.get("metadata", {}).get("source", "")
            total_triples += self.build_from_text(text, source=source, llm_client=llm_client)

        return {"triples_extracted": total_triples, **self.graph.summary()}

    def query(self, entity: str, max_hops: int = 2) -> List[Dict]:
        """Query graph relations from an entity"""
        if isinstance(self.graph, InMemoryGraph):
            return self.graph.query_relations(entity, max_hops)
        elif isinstance(self.graph, KuzuGraph):
            return self.graph.traverse(entity, max_hops)
        return []

    @property
    def summary(self) -> dict:
        return self.graph.summary()

    def save(self, path: str = None):
        """Persist graph to JSON (for InMemoryGraph)"""
        if isinstance(self.graph, InMemoryGraph):
            path = path or os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "wolf_data", "knowledge_graph", "graph.json"
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"nodes": self.graph.nodes, "edges": self.graph.edges}, f, indent=2)

    def load(self, path: str = None):
        """Load graph from JSON (for InMemoryGraph)"""
        path = path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "wolf_data", "knowledge_graph", "graph.json"
        )
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.graph.nodes = data.get("nodes", {})
                self.graph.edges = data.get("edges", [])


_kg_builder: Optional[AutoKGBuilder] = None


def get_kg_builder(db_path: str = None) -> AutoKGBuilder:
    global _kg_builder
    if _kg_builder is None:
        _kg_builder = AutoKGBuilder(db_path)
    return _kg_builder
