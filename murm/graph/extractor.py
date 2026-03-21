"""
Extracts entities and relations from seed documents using a two-pass LLM pipeline.

Pass 1 - Ontology generation: derive a domain-specific schema (entity types,
         relation types) from the document content. This bounds extraction to
         categories that actually appear, preventing hallucinated generic types.

Pass 2 - Entity extraction: populate nodes and edges from the document using
         the schema as a hard constraint.

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
    {"name": "string", "type": "string from ontology", "summary": "1–2 sentence description"}
  ],
  "relations": [
    {"source": "entity name", "target": "entity name", "relation": "relation type from ontology"}
  ]
}
Rules:
- entity names must be unique and canonical (use the most common form)
- only use entity types and relation types from the provided ontology
- relations must reference entity names that appear in your entity list
- AIM FOR EXTREME COMPLETENESS AND DENSTIY — extract a massive, highly interconnected web of node relationships representing even minor tangential details."""


@dataclass
class ExtractionResult:
    ontology: dict
    entities: list[dict]
    relations: list[dict]


class EntityExtractor:
    """
    Two-pass entity/relation extractor.
    Uses the orchestration-level LLMProvider (not the cheaper agent model).
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def extract(self, document_text: str, title: str = "Document") -> ExtractionResult:
        """
        Full two-pass extraction pipeline.
        document_text is the raw text of the seed material (truncated if very long).
        """
        text = _truncate(document_text, max_chars=24_000)

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
