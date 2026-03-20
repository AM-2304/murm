"""
Evaluation script for MURM paper experiments.

Runs the simulation pipeline on a set of benchmark seed documents and
prediction questions, collects emergence metrics and sensitivity results,
and writes them to CSV files for analysis.

Usage:
  python eval.py --seeds-file eval_seeds.json --output-dir results/ --k 3
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option("--seeds-file", type=click.Path(exists=True), required=True,
              help="JSON file with eval tasks: [{title, seed_text, question, expected_direction}]")
@click.option("--output-dir", type=click.Path(), default="results", show_default=True)
@click.option("--n-agents", type=int, default=50, show_default=True)
@click.option("--n-rounds", type=int, default=30, show_default=True)
@click.option("--k", type=int, default=3, show_default=True,
              help="Number of random seeds per task for sensitivity analysis")
@click.option("--base-seed", type=int, default=42, show_default=True)
@click.option("--opinion-dist", type=click.Choice(["normal", "bimodal", "power_law", "uniform"]),
              default="normal", show_default=True)
@click.option("--env-type", type=click.Choice(["forum", "town_hall"]),
              default="forum", show_default=True)
def main(seeds_file, output_dir, n_agents, n_rounds, k, base_seed, opinion_dist, env_type):
    """Run evaluation benchmark and write results to CSV."""
    asyncio.run(_run_eval(
        seeds_file=Path(seeds_file),
        output_dir=Path(output_dir),
        n_agents=n_agents,
        n_rounds=n_rounds,
        k=k,
        base_seed=base_seed,
        opinion_dist=opinion_dist,
        env_type=env_type,
    ))


async def _run_eval(seeds_file, output_dir, n_agents, n_rounds, k, base_seed, opinion_dist, env_type):
    from murm.analysis.calibration import compute_sensitivity, uncertainty_statement
    from murm.agents.generator import PersonaGenerator
    from murm.config import settings
    from murm.graph.embedder import Embedder
    from murm.graph.engine import KnowledgeGraph
    from murm.graph.extractor import EntityExtractor
    from murm.llm.budget import BudgetManager
    from murm.llm.provider import LLMProvider
    from murm.simulation.engine import SimulationConfig, SimulationEngine
    from murm.simulation.environment import build_environment
    from murm.simulation.trace import TraceWriter

    settings.ensure_dirs()
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = json.loads(seeds_file.read_text())
    logger.info("Loaded %d evaluation tasks", len(tasks))

    rows = []
    budget = BudgetManager(budget_tokens=0)
    llm = LLMProvider(budget=budget)

    for task_idx, task in enumerate(tasks):
        task_id = f"task_{task_idx:03d}"
        title = task.get("title", task_id)
        seed_text = task["seed_text"]
        question = task["question"]

        logger.info("[%d/%d] Task: %s", task_idx + 1, len(tasks), title)

        # Build graph
        project_id = f"eval_{task_id}_{base_seed}"
        graph_path = settings.data_dir / "projects" / project_id / "graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)

        extractor = EntityExtractor(llm)
        extraction = await extractor.extract(seed_text, title=title)
        kg = KnowledgeGraph(graph_path)
        embedder = Embedder(settings.chroma_path, project_id)
        for entity in extraction.entities:
            kg.add_entity(entity["name"], entity.get("type", "entity"), entity.get("summary", ""))
        for rel in extraction.relations:
            try:
                kg.add_relation(rel["source"], rel["target"], rel["relation"])
            except ValueError:
                pass
        embedder.upsert_batch([
            {"id": e["name"].lower().replace(" ", "_"), "text": f"{e['name']}: {e.get('summary','')}",
             "metadata": {"entity_type": e.get("type", "")}}
            for e in extraction.entities
        ])

        # Generate agents (same population across seeds for fair comparison)
        gen = PersonaGenerator(llm, seed=base_seed)
        agents = await gen.generate_population(
            n_agents=n_agents, topic=question,
            context=seed_text[:1500], opinion_dist=opinion_dist,
        )

        # Run k seeds
        all_metrics = []
        sim_base = settings.data_dir / "simulations" / task_id

        for seed_offset in range(k):
            actual_seed = base_seed + seed_offset
            logger.info("  Seed %d (%d/%d)", actual_seed, seed_offset + 1, k)

            sim_config = SimulationConfig(
                n_rounds=n_rounds, seed=actual_seed,
                environment_type=env_type, prediction_question=question,
            )
            env = build_environment(env_type, seed=actual_seed)
            trace_dir = sim_base / f"seed_{actual_seed}"
            engine = SimulationEngine(
                run_id=f"{task_id}_{actual_seed}",
                agents=agents, environment=env, config=sim_config,
                trace_dir=trace_dir, budget=budget, embedder=embedder,
            )
            completed = await engine.execute()
            seed_metrics = engine._metrics.final_summary()
            seed_metrics["seed"] = actual_seed
            seed_metrics["status"] = completed.status.value
            seed_metrics["total_actions"] = completed.total_actions
            all_metrics.append(seed_metrics)

        sensitivity = compute_sensitivity(all_metrics)

        row = {
            "task_id": task_id,
            "title": title,
            "question": question,
            "n_agents": n_agents,
            "n_rounds": n_rounds,
            "k_seeds": k,
            "opinion_dist": opinion_dist,
            "graph_entities": len(extraction.entities),
            "graph_relations": len(extraction.relations),
            "mean_final_entropy": sensitivity.mean_final_entropy,
            "std_final_entropy": sensitivity.std_final_entropy,
            "mean_polarization": sensitivity.mean_polarization,
            "std_polarization": sensitivity.std_polarization,
            "consensus_rate": sensitivity.consensus_rate,
            "prediction_variance": sensitivity.prediction_variance,
            "total_tokens": budget.snapshot()["total_tokens"],
            "estimated_cost_usd": budget.snapshot()["estimated_cost_usd"],
        }
        rows.append(row)
        logger.info("  Final entropy: %.3f±%.3f  Polarization: %.3f  Variance: %s",
                    sensitivity.mean_final_entropy, sensitivity.std_final_entropy,
                    sensitivity.mean_polarization, sensitivity.prediction_variance)

    # Write summary CSV
    csv_path = output_dir / "results_summary.csv"
    if rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    logger.info("Results written to %s", csv_path)

    # Write full metrics per seed
    full_path = output_dir / "results_per_seed.json"
    full_path.write_text(json.dumps(rows, indent=2))
    logger.info("Per-seed details written to %s", full_path)
    logger.info("Total budget used: %s", budget.snapshot())


if __name__ == "__main__":
    main()
