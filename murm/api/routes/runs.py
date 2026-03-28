"""
Run lifecycle routes.

Endpoints:
  GET  /api/runs/estimate          Pre-flight cost estimate (no LLM calls)
  POST /api/runs/                  Create and start a run
  GET  /api/runs/{run_id}          Run status + config
  GET  /api/runs/{run_id}/report   Completed markdown report
  GET  /api/runs/{run_id}/metrics  Emergence metrics time series
  POST /api/runs/{run_id}/cancel   Cancel a running simulation
  DELETE /api/runs/{run_id}        Delete run record and trace files
  POST /api/runs/{run_id}/interview  In-character agent interview
  POST /api/runs/{run_id}/inject   God-view: inject an event mid-simulation
  POST /api/runs/{run_id}/chat     Chat with the ReportAgent post-simulation
  POST /api/runs/{run_id}/resolve  Resolve a prediction with ground truth (Brier Score)
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from murm.analysis.calibration import compute_sensitivity as sensitivity_analysis
from murm.analysis.report_agent import ReportAgent
from murm.agents.generator import PersonaGenerator
from murm.agents.interviewer import AgentInterviewer
from murm.config import settings
from murm.graph.embedder import Embedder
from murm.graph.engine import KnowledgeGraph
from murm.llm.budget import BudgetManager
from murm.llm.provider import LLMProvider
from murm.simulation.engine import SimulationConfig, SimulationEngine
from murm.simulation.environment import build_environment
from murm.simulation.trace import TraceWriter
from murm.api.store import ProjectStore

logger = logging.getLogger(__name__)
router = APIRouter(tags=["runs"])

# Active engines indexed by run_id — used for cancel and live event injection
_active_engines: dict[str, SimulationEngine] = {}

# Post-simulation report agent instances — used for chat
_report_agents: dict[str, ReportAgent] = {}


class CreateRunRequest(BaseModel):
    project_id:            str
    prediction_question:   str
    n_agents:              int = Field(default=5,  ge=1,  le=500)
    n_rounds:              int = Field(default=5,  ge=1,  le=200)
    seed:                  int = Field(default=42)
    n_sensitivity_seeds:   int = Field(default=1,  ge=1,  le=5)
    environment_type:      str = Field(default="forum")
    opinion_distribution:  str = Field(default="normal")
    scenario_description:  str = Field(default="")
    counterfactual_events: list[dict] = Field(default_factory=list)
    skip_graph:            bool = Field(default=False)
    expert_mode:           bool = Field(default=False)


# ---------------------------------
# GET /api/runs/estimate
# ---------------------------------

@router.get("/estimate")
async def estimate_cost(
    agents: int = 5,
    rounds: int = 5,
    seeds:  int = 1,
) -> dict:
    return BudgetManager.estimate_simulation_cost(
        n_agents=agents,
        n_rounds=rounds,
        n_seeds=seeds,
        model=settings.llm_model,
    )


# ---------------------------------
# POST /api/runs/
# ---------------------------------

@router.post("/")
async def create_run(body: CreateRunRequest, request: Request) -> dict:
    store: ProjectStore = request.app.state.store

    project = await store.get_project(body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if not body.skip_graph and project.get("status") not in ("ready",):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Project graph is not ready (status={project.get('status')}). "
                "Build the graph first or pass skip_graph=true."
            ),
        )

    run_id = str(uuid.uuid4())
    config = body.model_dump()
    await store.create_run(run_id, body.project_id, config)

    asyncio.create_task(
        _run_simulation_safe(run_id, config, store, request.app)
    )

    return {"run_id": run_id, "status": "running"}


# ---------------------------------
# GET /api/runs/{run_id}
# ---------------------------------

@router.get("/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ---------------------------------
# GET /api/runs/{run_id}/report
# ---------------------------------

@router.get("/{run_id}/report")
async def get_report(run_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    report = run.get("report_md", "")
    if not report:
        raise HTTPException(status_code=404, detail="Report not yet available")
    return {"run_id": run_id, "report": report}


# ---------------------------------
# GET /api/runs/{run_id}/metrics
# ---------------------------------

@router.get("/{run_id}/metrics")
async def get_metrics(run_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    events = await store.get_events(run_id, since=0)
    metrics_history = []
    for ev in events:
        if ev.get("type") == "round_completed":
            payload = ev.get("payload", {})
            metrics_history.append({
                "round": payload.get("round"),
                **(payload.get("metrics") or {}),
            })
    return {"run_id": run_id, "metrics_history": metrics_history}


# ---------------------------------
# POST /api/runs/{run_id}/cancel
# ---------------------------------

@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    engine = _active_engines.get(run_id)
    if engine:
        engine.cancel()
        _active_engines.pop(run_id, None)
    await store.update_run(run_id, status="cancelled", completed_at=time.time())
    return {"run_id": run_id, "status": "cancelled"}


# ---------------------------------
# DELETE /api/runs/{run_id}
# ---------------------------------

@router.delete("/{run_id}")
async def delete_run(run_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    sim_dir = settings.data_dir / "simulations" / run_id
    if sim_dir.exists():
        shutil.rmtree(sim_dir, ignore_errors=True)
    await store.delete_run(run_id)
    _active_engines.pop(run_id, None)
    _report_agents.pop(run_id, None)
    return {"run_id": run_id, "deleted": True}


# ---------------------------------
# POST /api/runs/{run_id}/inject  (god-view event injection)
# ---------------------------------

@router.post("/{run_id}/inject")
async def inject_event(run_id: str, request: Request) -> dict:
    """
    Inject a counterfactual event into a running simulation.
    The event appears in the environment feed on the next round.
    This is MiroFish's "god view" feature — fully implemented here.
    """
    body = await request.json()
    content = body.get("content", "").strip()
    source  = body.get("source", "external")
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    engine = _active_engines.get(run_id)
    if engine is None:
        raise HTTPException(
            status_code=409,
            detail="No active simulation found for this run_id. "
                   "The run may have already completed or been cancelled."
        )

    # Inject directly into the live environment
    current_round = engine._run.current_round
    engine._env.inject_external_event(
        content=content, source=source, round_num=current_round
    )
    await engine._emit("event_injected", {
        "round":   current_round,
        "content": content,
        "source":  source,
        "injected_live": True,
    })

    # Fire and forget graph update
    async def _update_graph(text: str, rid: str):
        try:
            store: ProjectStore = request.app.state.store
            run = await store.get_run(rid)
            if not run: return
            project_id = run.get("config", {}).get("project_id")
            if not project_id: return
            
            graph_path = settings.data_dir / "projects" / project_id / "graph.json"
            if not graph_path.exists(): return
            
            from murm.llm.budget import BudgetManager
            from murm.llm.provider import LLMProvider
            from murm.graph.extractor import EntityExtractor
            from murm.graph.engine import KnowledgeGraph
            from murm.graph.embedder import Embedder
            
            b = BudgetManager(settings.token_budget)
            llm = LLMProvider(budget=b)
            extractor = EntityExtractor(llm)
            
            # Extract entities from the injected context
            res = await extractor.extract(text, f"Injected context (Round {current_round})")
            
            # Update the physical JSON Knowledge Graph
            kg = KnowledgeGraph(graph_path)
            for e in res.entities:
                kg.add_entity(e["name"], e["type"], e.get("desc", ""))
            for r in res.relations:
                try:
                    kg.add_relation(r["source"], r["target"], r["relation"])
                except ValueError:
                    pass # ignore missing source/target edges
                    
            # Update the vector store if possible
            try:
                emb = Embedder(settings.chroma_path, project_id)
                emb.insert(text, {"source": source, "round": current_round, "type": "god_mode_injection"})
            except Exception as e:
                logger.warning("Failed to update embedder for injection: %s", e)
                
        except Exception as e:
            logger.error("Failed to extract graph entities for injected event: %s", e)
            
    asyncio.create_task(_update_graph(content, run_id))

    return {
        "injected":       True,
        "content":        content,
        "injected_round": current_round,
    }


# ---------------------------------
# POST /api/runs/{run_id}/interview  (agent in-character interview)
# ---------------------------------

@router.post("/{run_id}/interview")
async def interview_agents(run_id: str, request: Request) -> dict:
    """
    Ask any agent a question. They respond in character based on their
    persona and what they actually posted during the simulation.
    """
    store: ProjectStore = request.app.state.store
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    body      = await request.json()
    question  = body.get("question", "").strip()
    agent_ids = body.get("agent_ids", [])
    if not question:
        raise HTTPException(status_code=422, detail="question is required")

    sim_dir = settings.data_dir / "simulations" / run_id
    last_seed = run.get("config", {}).get("seed", 42) + run.get("config", {}).get("n_sensitivity_seeds", 1) - 1
    run_dir = sim_dir / f"seed_{last_seed}"

    if not (run_dir / "agents.json").exists():
        raise HTTPException(status_code=404, detail='Agent records not found. The simulation may not have completed successfully or was run on an older version = "0.3.0"')

    budget = BudgetManager(settings.token_budget)
    llm    = LLMProvider(budget=budget)
    try:
        interviewer = AgentInterviewer(run_dir, llm)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not agent_ids:
        agent_ids = [a["agent_id"] for a in interviewer.list_agents()[:5]]

    responses: dict[str, str] = {}
    for aid in agent_ids:
        responses[aid] = await interviewer.interview_agent(aid, question)

    return {"responses": responses, "question": question}


# ---------------------------------
# POST /api/runs/{run_id}/chat  (chat with ReportAgent post-simulation)
# ---------------------------------

@router.post("/{run_id}/chat")
async def chat_with_report_agent(run_id: str, request: Request) -> dict:
    """
    Follow-up chat with the report agent after simulation.
    The agent retains context from the simulation and can answer
    specific questions about the results, methodology, or evidence.
    This is MiroFish's Step 5 deep interaction feature.
    """
    store: ProjectStore = request.app.state.store
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Run has not completed yet")

    body    = await request.json()
    message = body.get("message", "").strip()
    history = body.get("history", [])  # list of {role, content} dicts
    if not message:
        raise HTTPException(status_code=422, detail="message is required")

    # Load simulation context for grounding
    report   = run.get("report_md", "")
    sim_dir  = settings.data_dir / "simulations" / run_id
    trace_path = None
    for seed_dir in sorted(sim_dir.iterdir()) if sim_dir.exists() else []:
        c = seed_dir / "trace.jsonl"
        if c.exists():
            trace_path = c; break

    actions_sample = ""
    if trace_path:
        try:
            all_a = TraceWriter(trace_path).read_all()
            sample = all_a[::max(1, len(all_a) // 20)][:20]
            actions_sample = "\n".join(
                f"R{a.get('round')} [{a.get('opinion_shift','')}]: {(a.get('content',''))[:100]}"
                for a in sample if a.get("content")
            )
        except Exception:
            pass

    # Build conversation with full context in system prompt
    config  = run.get("config", {})
    system  = (
        "You are an expert simulation analyst who ran the following prediction study.\n\n"
        f"PREDICTION QUESTION: {config.get('prediction_question', '')}\n\n"
        f"SIMULATION: {config.get('n_agents')} agents, {config.get('n_rounds')} rounds.\n\n"
        f"REPORT:\n{report[:3000]}\n\n"
        f"AGENT ACTIONS SAMPLE:\n{actions_sample[:1500]}\n\n"
        "Answer the user's follow-up questions using the simulation evidence above. "
        "Be specific and cite evidence from the report and agent actions."
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    for h in history[-8:]:  # keep last 8 turns of context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    budget = BudgetManager(settings.token_budget)
    llm    = LLMProvider(budget=budget)
    try:
        response = await llm.complete(
            messages=messages, temperature=0.4, max_tokens=600,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM error: {exc}")

    return {"response": response, "role": "assistant"}
@router.post("/{run_id}/resolve")
async def resolve_run(run_id: str, request: Request) -> dict:
    """
    Submit ground truth for a completed simulation.
    Calculates the Brier score for the prediction.
    """
    store: ProjectStore = request.app.state.store
    body = await request.json()
    ground_truth = body.get("ground_truth")
    if not ground_truth:
        raise HTTPException(status_code=422, detail="ground_truth is required")
    
    try:
        result = await store.resolve_run(run_id, ground_truth)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------
# Background simulation task
# ---------------------------------

async def _run_simulation_safe(
    run_id: str,
    config: dict,
    store:  ProjectStore,
    app:    Any,
) -> None:
    """Global 20-minute timeout wrapper around the simulation body."""
    try:
        await asyncio.wait_for(
            _simulation_body(run_id, config, store, app),
            timeout=1200.0,
        )
    except asyncio.TimeoutError:
        logger.error("Run %s timed out after 20 minutes", run_id)
        _active_engines.pop(run_id, None)
        await store.update_run(
            run_id, status="failed", completed_at=time.time(),
            error="Run timed out after 20 minutes. Use fewer agents/rounds.",
        )
    except Exception as exc:
        logger.exception("Run %s outer handler: %s", run_id, exc)
        _active_engines.pop(run_id, None)
        await store.update_run(
            run_id, status="failed", completed_at=time.time(), error=str(exc),
        )


async def _simulation_body(
    run_id: str,
    config: dict,
    store:  ProjectStore,
    app:    Any,
) -> None:
    await store.update_run(run_id, status="running")
    try:
        project_id = config["project_id"]
        project    = await store.get_project(project_id)
        graph_path = settings.data_dir / "projects" / project_id / "graph.json"
        sim_dir    = settings.data_dir / "simulations" / run_id
        sim_dir.mkdir(parents=True, exist_ok=True)

        budget = BudgetManager(settings.token_budget)
        llm    = LLMProvider(budget=budget)

        skip_graph = config.get("skip_graph", False)
        embedder   = None
        if not skip_graph and graph_path.exists():
            try:
                embedder = Embedder(settings.chroma_path, project_id)
            except Exception:
                logger.warning("Could not load embedder for project %s", project_id)

        # Generate agent population
        # Fetch institutional entities to spawn dedicated representative agents
        institutions = []
        if not skip_graph and graph_path.exists():
            try:
                kg = KnowledgeGraph(graph_path)
                # Look for entities explicitly categorised as 'organization' in the graph
                institutions = [e for e in kg.entities() if e.get("category") == "organization"]
                logger.info("Found %d institutional entities to represent", len(institutions))
            except Exception as e:
                logger.warning("Could not fetch institutions from graph: %s", e)

        persona_gen = PersonaGenerator(llm, seed=config["seed"])
        agents = await persona_gen.generate_population(
            n_agents=config["n_agents"],
            topic=config["prediction_question"],
            context=(project.get("seed_text", "") or "")[:2000],
            opinion_dist=config.get("opinion_distribution", "normal"),
            institutions=institutions if institutions else None,
        )

        await store.add_event(run_id, {
            "type": "agents_ready",
            "timestamp": time.time(),
            "payload": {
                "n_agents": len(agents),
                "profiles": [
                    {
                        "agent_id":    a.agent_id,
                        "name":        a.name,
                        "occupation":  a.occupation,
                        "age":         a.age,
                        "opinion_bias": a.opinion_bias.value,
                        "influence_role": a.influence_role.value,
                        "expertise_domains": a.expertise_domains,
                    }
                    for a in agents
                ],
            },
        })

        n_seeds    = config.get("n_sensitivity_seeds", 1)
        all_metrics: list[dict] = []
        final_engine = None
        event_queue  = asyncio.Queue(maxsize=2000)

        for seed_offset in range(n_seeds):
            actual_seed = config["seed"] + seed_offset
            seed_dir    = sim_dir / f"seed_{actual_seed}"
            seed_dir.mkdir(parents=True, exist_ok=True)

            sim_config = SimulationConfig(
                n_rounds=config["n_rounds"],
                seed=actual_seed,
                environment_type=config["environment_type"],
                scenario_description=config.get("scenario_description", ""),
                prediction_question=config["prediction_question"],
                counterfactual_events=config.get("counterfactual_events", []),
            )
            env = build_environment(
                env_type=config["environment_type"],
                scenario_description=config.get("scenario_description", ""),
            )
            engine = SimulationEngine(
                run_id=f"{run_id}_seed{actual_seed}",
                agents=agents,
                environment=env,
                config=sim_config,
                trace_dir=seed_dir,
                budget=budget,
                event_queue=event_queue,
                embedder=embedder,
            )
            _active_engines[run_id] = engine

            # Bridge events from engine queue to the store (for SSE streaming)
            async def _bridge():
                while True:
                    try:
                        event = event_queue.get_nowait()
                        await store.add_event(run_id, event)
                    except asyncio.QueueEmpty:
                        break

            sim_task = asyncio.create_task(engine.execute())
            while not sim_task.done():
                await _bridge()
                await asyncio.sleep(0.1)
            await _bridge()

            result = await sim_task
            all_metrics.append(engine._metrics.final_summary())
            final_engine = engine

        _active_engines.pop(run_id, None)

        # Sensitivity analysis across seeds
        sensitivity = sensitivity_analysis(all_metrics).__dict__ if len(all_metrics) > 1 else {}

        # Find the trace for reporting
        last_seed = config["seed"] + n_seeds - 1
        trace_dir = sim_dir / f"seed_{last_seed}"
        trace_path_for_report = trace_dir / "trace.jsonl"

        kg = KnowledgeGraph(graph_path if graph_path.exists() else sim_dir / "stub_graph.json")
        if not graph_path.exists():
            kg._graph  # trigger empty init
        embedder_for_report = embedder or (
            Embedder(settings.chroma_path, f"stub_{run_id[:8]}")
        )
        trace_for_report = TraceWriter(
            trace_path_for_report if trace_path_for_report.exists()
            else (sim_dir / f"seed_{config['seed']}" / "trace.jsonl")
        )

        merged_metrics = all_metrics[-1] if all_metrics else {}
        merged_metrics["sensitivity"] = sensitivity

        report_agent = ReportAgent(
            llm=llm,
            graph=kg,
            embedder=embedder_for_report,
            trace=trace_for_report,
            metrics_summary=merged_metrics,
            simulation_config=config,
        )
        _report_agents[run_id] = report_agent

        await store.add_event(run_id, {
            "type": "system_log",
            "timestamp": time.time(),
            "payload": {"message": "Generating prediction report (expert mode)..." if config.get("expert_mode") else "Generating prediction report..."},
        })

        report_md = await report_agent.generate(
            config["prediction_question"], 
            mode="expert" if config.get("expert_mode") else "basic"
        )

        await store.update_run(
            run_id,
            status="completed",
            completed_at=time.time(),
            report_md=report_md,
            metrics=merged_metrics,
        )
        logger.info("Run %s completed successfully", run_id)

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        _active_engines.pop(run_id, None)
        await store.update_run(
            run_id, status="failed", completed_at=time.time(), error=str(exc),
        )