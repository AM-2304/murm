import sys, asyncio, httpx, json

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as c:
        proj = await c.post("/api/projects/", json={"title": "TestSSE", "seed_text": "AI markets."})
        pid = proj.json()["project_id"]
        run = await c.post("/api/runs/", json={"project_id": pid, "prediction_question": "Test", "n_agents": 3, "n_rounds": 3, "skip_graph": True})
        rid = run.json()["run_id"]
        
        async with c.stream("GET", f"/api/stream/{rid}?since=0") as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    print(line)
                    if "simulation_ended" in line or "done" in line:
                        break

asyncio.run(test())
