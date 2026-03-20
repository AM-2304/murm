import asyncio
from murm.api.store import ProjectStore
from murm.config import settings
from murm.graph.embedder import Embedder
from murm.graph.engine import KnowledgeGraph
from murm.graph.extractor import EntityExtractor
from murm.llm.budget import BudgetManager
from murm.llm.provider import LLMProvider

async def test():
    budget = BudgetManager(0)
    llm = LLMProvider(budget=budget)
    extractor = EntityExtractor(llm)
    seed_text = "The city council voted 7-2 to ban short-term rentals."
    try:
        result = await extractor.extract(seed_text, "test")
        print("Extraction success:", len(result.entities))
        
        graph_dir = settings.data_dir / "projects" / "test_proj"
        graph_dir.mkdir(parents=True, exist_ok=True)
        kg = KnowledgeGraph(graph_dir / "graph.json")
        embedder = Embedder(settings.chroma_path, "test_proj")
        
        for e in result.entities:
            kg.add_entity(e["name"], e.get("type", "entity"), e.get("summary", ""))
            
        print("KG Add success")
        embedder.upsert_batch([{"id": "doc1", "text": "test", "metadata": {}}])
        print("Embedder Upsert success")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
