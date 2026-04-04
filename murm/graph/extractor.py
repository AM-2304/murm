"""
Extracts entities and relations from seed documents using a two-pass LLM pipeline.

Pass 1 - Ontology generation: derive a domain-specific schema (entity types,
         relation types) from the document content. This bounds extraction to
         categories that actually appear, preventing hallucinated generic types.

Pass 2 - Entity extraction: populate nodes and edges from the document using
         the schema as a hard constraint.

Multi-document mode: each document is extracted independently, then merged
by canonical entity name. A final cross-document relation pass discovers
connections between entities that span different source documents.

The extractor is stateless and idempotent - feed it the same document twice
and you get the same output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from murm.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_ONTOLOGY_SYSTEM = """You are an elite knowledge graph ontologist mapping comprehensive domain models.
Given a document, derive an exhaustive, highly-detailed domain-specific ontology.
Return ONLY valid JSON matching this schema exactly:
{
  "entity_types": ["string", ...],
  "relation_types": ["string", ...]
}
entity_types: 15–30 diverse categories of real-world entities that appear in the document (e.g. key figures, organizations, metrics, regulations, sentiments, events, technologies).
relation_types: 25–45 specific and meaningful predicates describing exact relationships connecting those entity types.
Scale your output to capture high-resolution nuance; do not invent types entirely absent from the text, but map every underlying concept."""

_EXTRACT_SYSTEM = """You are a knowledge graph extractor.
Given a document and an ontology, extract all entities and relations.
Return ONLY valid JSON matching this schema exactly:
{
  "entities": [
    {"name": "string", "type": "string from ontology", "category": "individual|organization|other", "summary": "1–2 sentence description"}
  ],
  "relations": [
    {"source": "entity name", "target": "entity name", "relation": "relation type from ontology"}
  ]
}
Rules:
- entity names must be unique and canonical (use the most common form)
- only use entity types and relation types from the provided ontology
- relations must reference entity names that appear in your entity list
- AIM FOR EXTREME COMPLETENESS AND DENSITY, but LIMIT your output to a maximum of 40 entities and 60 relations to ensure your JSON string finishes successfully without getting cut off."""


@dataclass
class ExtractionResult:
    ontology: dict
    entities: list[dict]
    relations: list[dict]


class EntityExtractor:
    """
    Two-pass entity/relation extractor.
    Uses the orchestration-level LLMProvider (not the cheaper agent model).
    Supports both single-document and multi-document extraction.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def extract(self, document_text: str, title: str = "Document") -> ExtractionResult:
        """
        Full two-pass extraction pipeline for a single document.
        document_text is the raw text of the seed material (truncated if very long).
        """
        text = _truncate(document_text, max_chars=12_000)

        logger.info("Pass 1: ontology generation for '%s'", title)
        ontology = await self._generate_ontology(text, title)

        logger.info(
            "Pass 2: entity extraction (%d entity types, %d relation types)",
            len(ontology.get("entity_types", [])),
            len(ontology.get("relation_types", [])),
        )
        extraction = await self._extract_entities(text, ontology)

        entities = extraction.get("entities", [])
        relations = _filter_valid_relations(extraction.get("relations", []), entities)

        logger.info(
            "Extracted %d entities and %d relations", len(entities), len(relations)
        )
        return ExtractionResult(
            ontology=ontology,
            entities=entities,
            relations=relations,
        )

    async def extract_multi(
        self, documents: list[tuple[str, str]]
    ) -> ExtractionResult:
        """
        Multi-document extraction pipeline.

        documents: list of (document_text, title) tuples.

        Each document is extracted independently (own ontology + entities),
        then results are merged by canonical entity name. Entities appearing
        in multiple documents get their summaries fused. A final cross-document
        relation pass discovers connections between entities from different
        source documents.
        """
        if len(documents) == 1:
            return await self.extract(documents[0][0], documents[0][1])

        logger.info("Multi-document extraction: %d documents", len(documents))

        # Phase 1: Extract each document independently
        per_doc_results: list[ExtractionResult] = []
        for i, (text, title) in enumerate(documents):
            logger.info("  Extracting document %d/%d: '%s'", i + 1, len(documents), title)
            result = await self.extract(text, title)
            # Tag entities with source document for provenance
            for entity in result.entities:
                entity["source_document"] = title
            per_doc_results.append(result)

        # Phase 2: Merge ontologies (union of all types)
        merged_entity_types: set[str] = set()
        merged_relation_types: set[str] = set()
        for r in per_doc_results:
            merged_entity_types.update(r.ontology.get("entity_types", []))
            merged_relation_types.update(r.ontology.get("relation_types", []))

        merged_ontology = {
            "entity_types": sorted(merged_entity_types),
            "relation_types": sorted(merged_relation_types),
        }

        # Phase 3: Merge entities by canonical name
        entity_map: dict[str, dict] = {}  # canonical_name -> merged entity
        for r in per_doc_results:
            for entity in r.entities:
                canonical = entity["name"].strip().lower()
                if canonical in entity_map:
                    existing = entity_map[canonical]
                    # Fuse summaries from different documents
                    existing_summary = existing.get("summary", "")
                    new_summary = entity.get("summary", "")
                    if new_summary and new_summary not in existing_summary:
                        existing["summary"] = (
                            existing_summary + " | " + new_summary
                            if existing_summary
                            else new_summary
                        )
                    # Track source documents
                    sources = existing.get("source_documents", [existing.get("source_document", "unknown")])
                    sources.append(entity.get("source_document", "unknown"))
                    existing["source_documents"] = list(set(sources))
                else:
                    entity_map[canonical] = dict(entity)
                    entity_map[canonical]["source_documents"] = [
                        entity.get("source_document", "unknown")
                    ]

        merged_entities = list(entity_map.values())

        # Phase 4: Merge relations (union, deduplicated)
        merged_relations: list[dict] = []
        seen_triples: set[tuple] = set()
        for r in per_doc_results:
            valid = _filter_valid_relations(r.relations, merged_entities)
            for rel in valid:
                triple = (
                    rel["source"].strip().lower(),
                    rel["target"].strip().lower(),
                    rel["relation"].strip().lower(),
                )
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    merged_relations.append(rel)

        # Phase 5: Cross-document relation discovery
        # Find entities that appear in multiple documents — these are the bridging nodes
        cross_doc_entities = [
            e for e in merged_entities
            if len(e.get("source_documents", [])) > 1
        ]
        if cross_doc_entities and len(documents) > 1:
            logger.info(
                "  Cross-document pass: %d shared entities across documents",
                len(cross_doc_entities),
            )
            cross_relations = await self._discover_cross_relations(
                merged_entities, merged_ontology, cross_doc_entities
            )
            for rel in cross_relations:
                triple = (
                    rel["source"].strip().lower(),
                    rel["target"].strip().lower(),
                    rel["relation"].strip().lower(),
                )
                if triple not in seen_triples:
                    seen_triples.add(triple)
                    merged_relations.append(rel)

        logger.info(
            "Multi-document merge complete: %d entities, %d relations (from %d documents)",
            len(merged_entities),
            len(merged_relations),
            len(documents),
        )

        return ExtractionResult(
            ontology=merged_ontology,
            entities=merged_entities,
            relations=merged_relations,
        )

    # Passes

    async def _generate_ontology(self, text: str, title: str) -> dict:
        messages = [
            {"role": "system", "content": _ONTOLOGY_SYSTEM},
            {
                "role": "user",
                "content": f"Document title: {title}\n\n{text[:8_000]}",
            },
        ]
        result = await self._llm.complete_json(messages, temperature=0.1)
        if not isinstance(result, dict):
            raise ValueError("Ontology response was not a JSON object")
        return result

    async def _extract_entities(self, text: str, ontology: dict) -> dict:
        ontology_str = (
            f"Entity types: {', '.join(ontology.get('entity_types', []))}\n"
            f"Relation types: {', '.join(ontology.get('relation_types', []))}"
        )
        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": f"Ontology:\n{ontology_str}\n\nDocument:\n{text}",
            },
        ]
        result = await self._llm.complete_json(messages, temperature=0.1, max_tokens=8192)
        if not isinstance(result, dict):
            raise ValueError("Extraction response was not a JSON object")
        return result

    async def _discover_cross_relations(
        self,
        all_entities: list[dict],
        ontology: dict,
        cross_doc_entities: list[dict],
    ) -> list[dict]:
        """LLM pass to discover relations between entities from different documents."""
        entity_summaries = "\n".join(
            f"- {e['name']} ({e.get('type', 'entity')}): {e.get('summary', '')[:100]}"
            for e in all_entities[:40]  # cap to stay within token budget
        )
        cross_names = ", ".join(e["name"] for e in cross_doc_entities[:15])
        relation_types = ", ".join(ontology.get("relation_types", []))

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a knowledge graph analyst. Given a list of entities extracted "
                    "from multiple documents, discover relationships that connect entities "
                    "across different source documents. Focus especially on bridging entities "
                    "that appear in multiple documents.\n"
                    "Return ONLY valid JSON: {\"relations\": [{\"source\": \"name\", "
                    '\"target\": \"name\", \"relation\": \"type from ontology\"}]}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Available relation types: {relation_types}\n\n"
                    f"Entities shared across documents: {cross_names}\n\n"
                    f"All entities:\n{entity_summaries}\n\n"
                    "Discover 5-15 cross-document relations. Only use entity names "
                    "from the list above."
                ),
            },
        ]
        try:
            result = await self._llm.complete_json(messages, temperature=0.1, max_tokens=2048)
            relations = result.get("relations", []) if isinstance(result, dict) else []
            valid = _filter_valid_relations(relations, all_entities)
            logger.info("  Cross-document pass found %d new relations", len(valid))
            return valid
        except Exception as exc:
            logger.warning("Cross-document relation discovery failed: %s", exc)
            return []


# Helpers

def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    # Keep head and tail to preserve both context and conclusions
    half = max_chars // 2
    return text[:half] + "\n\n[... document truncated ...]\n\n" + text[-half:]


def _filter_valid_relations(relations: list[dict], entities: list[dict]) -> list[dict]:
    """Remove relations that reference entities not in the extracted entity list."""
    entity_names = {e["name"].lower().strip() for e in entities}
    valid = []
    for rel in relations:
        src = rel.get("source", "").lower().strip()
        tgt = rel.get("target", "").lower().strip()
        if src in entity_names and tgt in entity_names:
            valid.append(rel)
        else:
            logger.debug("Dropped relation with missing entity: %s -> %s", src, tgt)
    return valid
