"""
Semantic vector store using ChromaDB with local sentence-transformers embeddings.
Works entirely offline once the embedding model is downloaded.

The Embedder and KnowledgeGraph work as a pair:
  - KnowledgeGraph handles structural traversal (who knows whom, what caused what)
  - Embedder handles semantic retrieval (find entities relevant to a query)
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

# Default embedding model - runs locally via sentence-transformers.
# Override with CHROMA_EMBEDDING_MODEL env if you want a different model.
_DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"


class Embedder:
    """
    Thin wrapper around a ChromaDB collection for a single project's entities.
    Each project gets its own collection identified by project_id.
    """

    def __init__(self, chroma_path: Path, project_id: str) -> None:
        self._client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection_name = f"project_{project_id}"
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # Indexing

    def upsert_entity(self, entity_id: str, text: str, metadata: dict | None = None) -> None:
        """
        Add or update a single entity document.
        text should be a rich string combining name + summary + type for good retrieval.
        """
        self._collection.upsert(
            ids=[entity_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def upsert_batch(self, items: list[dict]) -> None:
        """
        Batch upsert. Each item: {"id": str, "text": str, "metadata": dict}.
        """
        if not items:
            return
        self._collection.upsert(
            ids=[i["id"] for i in items],
            documents=[i["text"] for i in items],
            metadatas=[i.get("metadata", {}) for i in items],
        )
        logger.debug("Upserted %d documents into collection %s", len(items), self._collection_name)

    # Retrieval

    def query(self, text: str, top_k: int = 10, entity_type: str | None = None) -> list[dict]:
        """
        Semantic nearest-neighbor search.
        Returns list of {"id": str, "text": str, "distance": float, "metadata": dict}.
        """
        where: dict | None = {"entity_type": entity_type} if entity_type else None
        kwargs: dict = dict(
            query_texts=[text],
            n_results=min(top_k, self._collection.count() or 1),
            include=["documents", "distances", "metadatas"],
        )
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        output = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            doc_id = results["ids"][0][results["documents"][0].index(doc)]
            output.append({"id": doc_id, "text": doc, "distance": dist, "metadata": meta})
        return output

    def count(self) -> int:
        return self._collection.count()

    def delete_collection(self) -> None:
        """Remove all vectors for this project — used when rebuilding a graph."""
        self._client.delete_collection(self._collection_name)
        logger.info("Deleted vector collection %s", self._collection_name)
