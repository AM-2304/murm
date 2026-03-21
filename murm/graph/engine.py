"""
Local knowledge graph backed by NetworkX.
Replaces Zep Cloud entirely - all data stays on disk.

Graph model:
  Nodes carry a 'type' attribute (entity category from the ontology).
  Edges carry a 'relation' attribute (relation type) and optionally 'weight'.
  The full graph is serialized to JSON on every mutation so restarts are free.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    Directed, typed knowledge graph with JSON persistence.
    Thread-safe for single-process concurrent reads; mutations must be serialized
    by callers (the graph builder already runs sequentially).
    """

    def __init__(self, graph_path: Path) -> None:
        self._path = graph_path
        self._g: nx.DiGraph = nx.DiGraph()
        if graph_path.exists():
            self._load()

    # Node operations

    def add_entity(
        self,
        name: str,
        entity_type: str,
        summary: str = "",
        **attrs: Any,
    ) -> str:
        """
        Add or update a named entity. Returns the node ID.
        Names are normalized to lowercase-stripped for deduplication.
        """
        node_id = _canonical_id(name)
        self._g.add_node(
            node_id,
            name=name,
            entity_type=entity_type,
            summary=summary,
            **attrs,
        )
        self._save()
        return node_id

    def get_entity(self, name: str) -> dict | None:
        node_id = _canonical_id(name)
        if node_id not in self._g:
            return None
        return dict(self._g.nodes[node_id])

    def entities(self, entity_type: str | None = None) -> list[dict]:
        result = []
        for nid, data in self._g.nodes(data=True):
            if entity_type is None or data.get("entity_type") == entity_type:
                result.append({"id": nid, **data})
        return result

    # Edge operations

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation: str,
        weight: float = 1.0,
        **attrs: Any,
    ) -> None:
        src = _canonical_id(source_name)
        tgt = _canonical_id(target_name)
        if src not in self._g or tgt not in self._g:
            raise ValueError(
                f"Both entities must exist before adding a relation: "
                f"'{source_name}' -> '{target_name}'"
            )
        self._g.add_edge(src, tgt, relation=relation, weight=weight, **attrs)
        self._save()

    def neighbors(self, name: str, relation: str | None = None) -> list[dict]:
        """Return outgoing neighbors of an entity, optionally filtered by relation type."""
        node_id = _canonical_id(name)
        if node_id not in self._g:
            return []
        result = []
        for _, tgt, edge_data in self._g.out_edges(node_id, data=True):
            if relation is None or edge_data.get("relation") == relation:
                node_data = dict(self._g.nodes[tgt])
                result.append({"id": tgt, **node_data, "relation": edge_data.get("relation")})
        return result

    # Search

    def search_entities(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Lexical search across entity names and summaries.
        Semantic search is handled by the Embedder companion class.
        Returns entities sorted by simple term-overlap score.
        """
        q_terms = set(query.lower().split())
        scored = []
        for nid, data in self._g.nodes(data=True):
            text = f"{data.get('name', '')} {data.get('summary', '')}".lower()
            score = sum(1 for t in q_terms if t in text)
            if score > 0:
                scored.append((score, {"id": nid, **data}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def subgraph_around(self, name: str, depth: int = 2) -> dict:
        """
        Return a serializable subgraph within 'depth' hops of the named entity.
        Useful for feeding local context into agent prompts.
        """
        node_id = _canonical_id(name)
        if node_id not in self._g:
            return {"nodes": [], "edges": []}
        reachable = nx.ego_graph(self._g, node_id, radius=depth)
        nodes = [{"id": n, **data} for n, data in reachable.nodes(data=True)]
        edges = [
            {"source": u, "target": v, **data}
            for u, v, data in reachable.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}

    # Serialization

    def to_dict(self) -> dict:
        return nx.node_link_data(self._g, edges="edges")

    def stats(self) -> dict:
        return {
            "n_entities": self._g.number_of_nodes(),
            "n_relations": self._g.number_of_edges(),
            "entity_types": _count_by(self._g.nodes(data=True), "entity_type"),
            "relation_types": _count_by(self._g.edges(data=True), "relation"),
        }

    # Internal

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._g, edges="edges")
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _load(self) -> None:
        data = json.loads(self._path.read_text())
        self._g = nx.node_link_graph(data, directed=True, edges="edges")
        logger.info("Loaded graph from %s (%d nodes, %d edges)",
                    self._path, self._g.number_of_nodes(), self._g.number_of_edges())


# Helpers

def _canonical_id(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _count_by(items: Any, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        val = item[-1].get(key, "unknown") if isinstance(item, tuple) else item.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts
