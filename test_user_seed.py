import asyncio
from murm.api.store import ProjectStore
from murm.config import settings
from murm.graph.embedder import Embedder
from murm.graph.engine import KnowledgeGraph
from murm.graph.extractor import EntityExtractor
from murm.llm.budget import BudgetManager
from murm.llm.provider import LLMProvider
import os

async def test():
    budget = BudgetManager(0)
    llm = LLMProvider(budget=budget)
    extractor = EntityExtractor(llm)
    seed_text = """Testing has revealed lead levels exceeding federal action thresholds in 23% of sampled residential taps in the city's older neighborhoods. The city council has issued a boil-water advisory for affected zones and announced an emergency infrastructure replacement program estimated at $340 million over 5 years. Low-income residents are disproportionately affected, as older housing stock correlates with income levels in the city. Community groups are organizing legal action. The mayor has acknowledged the failure of routine testing procedures and announced the resignation of the public works director."""
    
    try:
        result = await extractor.extract(seed_text, "Municipal Water Crisis")
        print("Extraction success:", len(result.entities))
        
        graph_dir = settings.data_dir / "projects" / "test_user_proj"
        graph_dir.mkdir(parents=True, exist_ok=True)
        kg = KnowledgeGraph(graph_dir / "graph.json")
        embedder = Embedder(settings.chroma_path, "test_user_proj")
        
        for e in result.entities:
            kg.add_entity(e["name"], e.get("type", "entity"), e.get("summary", ""))
            
        print("KG Add success")
        
        seen_ids = set()
        deduped_items = []
        for entity in result.entities:
            raw_id = entity["name"].strip().lower().replace(" ", "_")
            canonical = raw_id if raw_id not in seen_ids else f"{raw_id}_{entity.get('type','entity').lower()[:8]}"
            counter = 2
            while canonical in seen_ids:
                canonical = f"{raw_id}_{counter}"
                counter += 1
            seen_ids.add(canonical)
            deduped_items.append({
                "id": canonical,
                "text": f"{entity['name']} ({entity.get('type','')}): {entity.get('summary','')}",
                "metadata": {"entity_type": entity.get("type", ""), "project_id": "test_user_proj"},
            })
            
        if deduped_items:
            embedder.upsert_batch(deduped_items)
            print("Embedder Upsert success")
        else:
            print("Empty result, skipped upsert")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.environ["LLM_MODEL"] = "groq/llama-3.3-70b-versatile"
    asyncio.run(test())
