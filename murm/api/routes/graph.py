"""
Graph building endpoints.
Triggers the two-pass LLM extraction pipeline and builds the local KnowledgeGraph & ChromaDB.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from murm.api.store import ProjectStore
from murm.config import settings
from murm.graph.embedder import Embedder
from murm.graph.engine import KnowledgeGraph
from murm.graph.extractor import EntityExtractor
from murm.llm.budget import BudgetManager
from murm.llm.provider import LLMProvider
from murm.utils.text import extract_text_from_path

router = APIRouter()
logger = logging.getLogger(__name__)


class BuildGraphRequest(BaseModel):
    prediction_question: str = ""
    topic_hint: str = ""


@router.post("/{project_id}/build")
async def build_graph(
    project_id: str,
    body: BuildGraphRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict:
    store: ProjectStore = request.app.state.store
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await store.update_project(project_id, status="building_graph")
    background_tasks.add_task(
        _run_graph_build, project_id, body.dict(), store
    )
    return {"status": "building", "project_id": project_id}


@router.get("/{project_id}/graph")
async def get_graph(project_id: str, request: Request) -> dict:
    """Return the full serialized graph for frontend visualization."""
    graph_path = settings.data_dir / "projects" / project_id / "graph.json"
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graph not built yet")
    import json
    return json.loads(graph_path.read_text())


@router.get("/{project_id}/graph/stats")
async def graph_stats(project_id: str, request: Request) -> dict:
    graph_path = settings.data_dir / "projects" / project_id / "graph.json"
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Graph not built yet")
    g = KnowledgeGraph(graph_path)
    return g.stats()


@router.get("/{project_id}/graph/search")
async def search_graph(project_id: str, query: str, request: Request) -> list[dict]:
    """Semantic search over the project's knowledge graph entities."""
    embedder = Embedder(settings.chroma_path, project_id)
    results = embedder.query(query, top_k=10)
    return results



# Background task


async def _run_graph_build(project_id: str, body: dict, store: ProjectStore) -> None:
    try:
        project = await store.get_project(project_id)
        if project is None:
            return

        # Collect all document sources as (text, title) pairs
        documents: list[tuple[str, str]] = []

        seed_text = project.get("seed_text", "")
        if seed_text.strip():
            documents.append((seed_text, project.get("title", "inline_text")))

        upload_dir = settings.data_dir / "projects" / project_id / "uploads"
        for fname in project.get("seed_files", []):
            file_path = upload_dir / fname
            if file_path.exists():
                extracted = extract_text_from_path(file_path)
                if extracted.strip():
                    documents.append((extracted, file_path.stem))

        if not documents:
            await store.update_project(project_id, status="error")
            logger.error("Project %s has no seed text to extract from", project_id)
            return

        budget = BudgetManager(settings.token_budget)
        llm = LLMProvider(budget=budget)
        extractor = EntityExtractor(llm)

        # Use multi-document extraction when there are multiple sources
        result = await extractor.extract_multi(documents)

        graph_dir = settings.data_dir / "projects" / project_id
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph_path = graph_dir / "graph.json"

        kg = KnowledgeGraph(graph_path)
        embedder = Embedder(settings.chroma_path, project_id)

        for entity in result.entities:
            kg.add_entity(
                name=entity["name"],
                entity_type=entity.get("type", "entity"),
                summary=entity.get("summary", ""),
            )

        for relation in result.relations:
            try:
                kg.add_relation(
                    source_name=relation["source"],
                    target_name=relation["target"],
                    relation=relation["relation"],
                )
            except ValueError as exc:
                logger.debug("Skipping relation: %s", exc)

        # Index all entities into ChromaDB for semantic search
        # Deduplicate by canonical ID before upserting: ChromaDB rejects duplicate IDs
        seen_ids: set[str] = set()
        deduped_items = []
        for entity in result.entities:
            raw_id = entity["name"].strip().lower().replace(" ", "_")
            # Append entity type to break ties when two entities share the same canonical name
            canonical = raw_id if raw_id not in seen_ids else f"{raw_id}_{entity.get('type','entity').lower()[:8]}"
            # If still a duplicate after adding type, append a counter
            counter = 2
            while canonical in seen_ids:
                canonical = f"{raw_id}_{counter}"
                counter += 1
            seen_ids.add(canonical)
            metadata_val = entity.get("type", "")
            if not isinstance(metadata_val, (str, int, float, bool)):
                metadata_val = str(metadata_val)
            deduped_items.append({
                "id": canonical,
                "text": f"{entity['name']} ({metadata_val}): {entity.get('summary','')}",
                "metadata": {"entity_type": metadata_val, "project_id": str(project_id)},
            })
            
        if deduped_items:
            embedder.upsert_batch(deduped_items)

        await store.update_project(
            project_id,
            ontology=result.ontology,
            status="ready",
        )
        logger.info(
            "Graph built for project %s: %d entities, %d relations",
            project_id,
            len(result.entities),
            len(result.relations),
        )

    except Exception as exc:
        logger.exception("Graph build failed for project %s", project_id)
        await store.update_project(project_id, status="error")

