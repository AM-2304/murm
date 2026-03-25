"""
Command-line interface for MURM.
Provides programmatic access to the full pipeline without requiring the UI,
enabling scripted research runs and batch sensitivity analysis.

Usage:
  murm serve                    # Start the API server
  murm run --help               # Run a simulation from CLI
  murm estimate --help          # Pre-flight cost estimate
  murm calibrate --help         # Score a past prediction
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def main():
    """MURM - swarm intelligence prediction engine."""
    pass


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, default=False)
def serve(host: str, port: int, reload: bool):
    """Start the MURM API server."""
    import uvicorn
    uvicorn.run(
        "murm.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@main.command()
@click.option("--seed-file", type=click.Path(exists=True), required=False, multiple=True, help="Path to seed document(s) — repeatable for multi-document ingestion")
@click.option("--seed-text", type=str, required=False, help="Inline seed text")
@click.option("--question", type=str, required=True, help="Prediction question")
@click.option("--agents", type=int, default=50, show_default=True, help="Number of agents")
@click.option("--rounds", type=int, default=30, show_default=True, help="Simulation rounds")
@click.option("--seed", type=int, default=42, show_default=True, help="Base random seed")
@click.option("--seeds", type=int, default=1, show_default=True, help="Number of seed runs for sensitivity analysis")
@click.option("--env", type=click.Choice(["forum", "town_hall"]), default="forum", show_default=True)
@click.option(
    "--opinion-dist",
    type=click.Choice(["normal", "bimodal", "power_law", "uniform"]),
    default="normal",
    show_default=True,
)
@click.option(
    "--skip-graph",
    is_flag=True,
    default=False,
    help="Skip graph extraction; use raw seed text as agent context only",
)
@click.option(
    "--resample-agents",
    is_flag=True,
    default=False,
    help="Regenerate agent population independently for each seed (true Monte Carlo sensitivity)",
)
@click.option("--expert", is_flag=True, default=False, help="Run the expert multi-step report generation pipeline")
@click.option("--output", type=click.Path(), default="report.md", show_default=True)
def run(
    seed_file,
    seed_text,
    question,
    agents,
    rounds,
    seed,
    seeds,
    env,
    opinion_dist,
    skip_graph,
    resample_agents,
    expert,
    output,
):
    """Run a complete simulation and write the report to a file.

    Multi-document: pass --seed-file multiple times to merge several documents
    into a single unified knowledge graph with cross-document relation discovery.
    """
    asyncio.run(
        _run_pipeline(
            seed_files=list(seed_file),
            seed_text=seed_text,
            question=question,
            n_agents=agents,
            n_rounds=rounds,
            seed=seed,
            n_seeds=seeds,
            env_type=env,
            opinion_dist=opinion_dist,
            output_path=Path(output),
            skip_graph=skip_graph,
            resample_agents=resample_agents,
            expert_mode=expert,
        )
    )


@main.command()
@click.option("--agents", type=int, default=50)
@click.option("--rounds", type=int, default=30)
@click.option("--seeds", type=int, default=1)
def estimate(agents, rounds, seeds):
    """Print a pre-flight token and cost estimate for a simulation run.

    Note: includes extraction, persona generation, simulation, and report phases.
    """
    from murm.config import settings
    from murm.llm.budget import BudgetManager

    est = BudgetManager.estimate_simulation_cost(
        n_agents=agents,
        n_rounds=rounds * seeds,
        model=settings.llm_model,
    )
    table = Table(title="Cost Estimate", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    for k, v in est.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    console.print(table)


@main.command()
@click.option("--run-id", type=str, required=True, help="Run ID to resolve")
@click.option("--truth", type=str, required=True, help="Actual outcome (e.g. 'agree', 'disagree')")
def calibrate(run_id, truth):
    """Submit ground truth for a completed simulation and compute Brier score.
    
    This allows you to benchmark MURM's accuracy against real-world events.
    Calibration requires a local data directory with a murm.db present.
    """
    from murm.config import settings
    from murm.api.store import ProjectStore

    async def _resolve():
        store = ProjectStore(settings.data_dir / "murm.db")
        await store.initialize()
        try:
            res = await store.resolve_run(run_id, truth)
            table = Table(title=f"Calibration Result: {run_id[:8]}", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            table.add_row("Outcome Match", "YES" if res["match"] else "NO")
            table.add_row("Brier Score", f"{res['brier_score']:.4f}")
            table.add_row("Interpretation", "Perfect" if res["brier_score"] == 0 else "Good" if res["brier_score"] < 0.1 else "Poor")
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error resolving run: {e}[/red]")

    asyncio.run(_resolve())


async def _run_pipeline(
    seed_files: list[str],
    seed_text,
    question: str,
    n_agents: int,
    n_rounds: int,
    seed: int,
    n_seeds: int,
    env_type: str,
    opinion_dist: str,
    output_path: Path,
    skip_graph: bool = False,
    resample_agents: bool = False,
    expert_mode: bool = False,
) -> None:
    # Deferred imports keep CLI startup fast and avoid circular deps at module load
    from murm.config import settings
    from murm.graph.embedder import Embedder
    from murm.graph.engine import KnowledgeGraph
    from murm.graph.extractor import EntityExtractor
    from murm.agents.generator import PersonaGenerator
    from murm.analysis.calibration import compute_sensitivity, uncertainty_statement
    from murm.analysis.report_agent import ReportAgent
    from murm.llm.budget import BudgetManager
    from murm.llm.provider import LLMProvider
    from murm.simulation.engine import SimulationConfig, SimulationEngine
    from murm.simulation.environment import build_environment
    from murm.simulation.trace import TraceWriter
    from murm.utils.text import extract_text_from_path

    settings.ensure_dirs()
    run_id = str(uuid.uuid4())

    # Load and normalise seed content — supports multi-document
    documents: list[tuple[str, str]] = []  # (text, title) pairs
    if seed_files:
        for fpath in seed_files:
            p = Path(fpath)
            extracted = extract_text_from_path(p)
            if extracted.strip():
                documents.append((extracted, p.stem))
            else:
                console.print(f"[yellow]Warning: could not extract text from {p.name}[/yellow]")

    if seed_text:
        documents.append((seed_text, "inline_seed"))

    if not documents:
        console.print("[red]Provide --seed-file or --seed-text[/red]")
        sys.exit(1)

    # Combined text for agent context (all documents concatenated)
    text = "\n\n---\n\n".join(doc_text for doc_text, _ in documents)
    is_multi = len(documents) > 1

    console.print(f"[bold]MURM[/bold] run {run_id[:8]}")
    console.print(f"  Question: {question}")
    console.print(f"  Agents: {n_agents}  Rounds: {n_rounds}  Seeds: {n_seeds}")

    budget = BudgetManager(settings.token_budget)
    llm = LLMProvider(budget=budget)

    # Phase 1: Knowledge graph extraction (entire block is conditional on skip_graph)
    # kg and embedder remain None when skip_graph=True; ReportAgent must tolerate None.
    kg = None
    embedder = None

    if not skip_graph:
        extractor = EntityExtractor(llm)
        if is_multi:
            console.print(f"[cyan]Extracting knowledge graph from {len(documents)} documents (multi-document fusion)...[/cyan]")
            extraction = await extractor.extract_multi(documents)
        else:
            console.print("[cyan]Extracting knowledge graph...[/cyan]")
            extraction = await extractor.extract(text, title=documents[0][1])

        project_id = run_id
        graph_path = settings.data_dir / "projects" / project_id / "graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        kg = KnowledgeGraph(graph_path)
        embedder = Embedder(settings.chroma_path, project_id)

        for entity in extraction.entities:
            kg.add_entity(
                entity["name"],
                entity.get("type", "entity"),
                entity.get("summary", ""),
            )
        for rel in extraction.relations:
            try:
                kg.add_relation(rel["source"], rel["target"], rel["relation"])
            except ValueError:
                pass  # skip malformed or duplicate relation triples

        embedder.upsert_batch(
            [
                {
                    "id": e["name"].strip().lower().replace(" ", "_"),
                    "text": f"{e['name']}: {e.get('summary', '')}",
                    "metadata": {"entity_type": e.get("type", "")},
                }
                for e in extraction.entities
            ]
        )
        console.print(
            f"  Graph: {kg.stats()['n_entities']} entities, "
            f"{kg.stats()['n_relations']} relations"
        )

    # Phase 2: Generate base agent population
    # When resample_agents=True, this population is used only for seed 0;
    # subsequent seeds regenerate independently for true Monte Carlo sensitivity.
    console.print("[cyan]Generating agent population...[/cyan]")
    persona_gen = PersonaGenerator(llm, seed=seed)
    base_agents = await persona_gen.generate_population(
        n_agents=n_agents,
        topic=question,
        context=text[:1500],
        opinion_dist=opinion_dist,
    )

    # Phase 3: Multi-seed simulation loop
    all_metrics: list[dict] = []
    all_trace_paths: list[Path] = []
    sim_dir = settings.data_dir / "simulations" / run_id

    for seed_offset in range(n_seeds):
        actual_seed = seed + seed_offset
        console.print(
            f"[cyan]Running simulation seed {actual_seed} "
            f"({seed_offset + 1}/{n_seeds})...[/cyan]"
        )

        # Independent population draw per seed when measuring true sensitivity.
        # Without this, variance across seeds reflects only engine stochasticity,
        # not population sampling error, understating epistemic uncertainty.
        if resample_agents and seed_offset > 0:
            current_agents = await persona_gen.generate_population(
                n_agents=n_agents,
                topic=question,
                context=text[:1500],
                opinion_dist=opinion_dist,
            )
        else:
            current_agents = base_agents

        sim_config = SimulationConfig(
            n_rounds=n_rounds,
            seed=actual_seed,
            environment_type=env_type,
            prediction_question=question,
        )
        env = build_environment(env_type, seed=actual_seed)
        trace_dir = sim_dir / f"seed_{actual_seed}"
        trace_path = trace_dir / "trace.jsonl"

        engine = SimulationEngine(
            run_id=run_id,
            agents=current_agents,
            environment=env,
            config=sim_config,
            trace_dir=trace_dir,
            budget=budget,
        )
        completed = await engine.execute()
        all_metrics.append(engine._metrics.final_summary())
        all_trace_paths.append(trace_path)

        console.print(
            f"  Seed {actual_seed}: {completed.total_actions} actions, "
            f"status={completed.status.value}"
        )

    # Phase 4: Cross-seed sensitivity analysis
    sensitivity = compute_sensitivity(all_metrics)
    uncertainty = uncertainty_statement(sensitivity)

    # Phase 5: Report assembly from the final seed's trace
    # Future improvement: synthesise across all_trace_paths for multi-seed reports.
    console.print("[cyan]Generating report...[/cyan]")
    final_trace = TraceWriter(all_trace_paths[-1])
    final_metrics = all_metrics[-1].copy()
    final_metrics["sensitivity"] = sensitivity.__dict__

    report_agent = ReportAgent(
        llm=llm,
        graph=kg,
        embedder=embedder,
        trace=final_trace,
        metrics_summary=final_metrics,
        simulation_config={
            "prediction_question": question,
            "n_agents": n_agents,
            "n_rounds": n_rounds,
        },
    )
    report_md = await report_agent.generate(question, mode="expert" if expert_mode else "basic")

    # Format budget snapshot as readable key-value lines rather than raw dict repr
    budget_snapshot = budget.snapshot()
    if isinstance(budget_snapshot, dict):
        budget_lines = "\n".join(
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in budget_snapshot.items()
        )
    else:
        budget_lines = str(budget_snapshot)

    # Build Opinion Distribution line from final metrics
    dominant_op = final_metrics.get("dominant_opinion", "unknown")
    consensus_pct = final_metrics.get("consensus", 0)
    if isinstance(consensus_pct, (int, float)):
        consensus_pct = f"{int(consensus_pct * 100)}%"

    report_md = (
        report_md
        + f"\n\n## Uncertainty Assessment\n\n{uncertainty}"
        + f"\n\n## Opinion Distribution\n\nDominant: {dominant_op.replace('_', ' ')} {consensus_pct}"
        + f"\n\n## Token Usage\n\n{budget_lines}"
    )

    output_path.write_text(report_md, encoding="utf-8")
    console.print(f"[green]Report written to {output_path}[/green]")
    console.print(f"Token usage: {budget_lines}")