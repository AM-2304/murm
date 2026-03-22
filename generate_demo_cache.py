import asyncio
import os
import sys

# Ensure murm is in path
sys.path.insert(0, os.path.abspath('.'))

from murm.config import settings
from murm.api.app import run_simulation
from murm.simulation.environment import EnvironmentType
from tests.test_user_seed import get_example_seed

# Force demo cache saving
settings.demo_mode = True

async def main():
    print("Starting Demo Cache Generation...")
    print("This will hit the Groq API ONCE to generate the perfect flawless 5-agent, 5-round run.")
    print("After this finishes, you can safely deploy without API keys!")
    
    # Grab the central bank test case from eval_seeds
    seed = get_example_seed(1) # The 2nd scenario: Central Bank
    text = seed["text"]
    q = seed["question"]
    
    try:
        # We manually bypass the api endpoint requirement and just run the engine
        from murm.api.routes.runs import _run_simulation_task
        from murm.simulation.engine import SimulationEngine
        from murm.api.store import api_store
        
        print("\n[+] Setting up fake project/run...")
        p_id = api_store.create_project("Frozen Demo Project", text)
        r_id = api_store.create_run(
            project_id=p_id,
            question=q,
            agents=5,
            rounds=5,
            seed=42,
            environment=EnvironmentType.FORUM
        )
        
        print(f"[+] Engine running (Project {p_id[:4]}, Run {r_id[:4]})...")
        print("    Please wait a few minutes for the rounds to complete.")
        
        # Use litellm with actual API keys for this 1 single run
        engine = SimulationEngine(api_store.get_run(r_id), api_store.get_project(p_id).text)
        await engine.execute_run()
        
        print("\nCACHE GENERATION COMPLETE!")
        print("Check the 'demo/cache/' folder, it's now full of JSON snippets.")
        print("You are 100% safe to upload to GitHub Desktop!")
        
    except Exception as e:
        print(f"\n Error during cache generation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
