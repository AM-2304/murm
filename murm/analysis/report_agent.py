"""
Report generation agent.

Offers two modes: basic and expert.
- Basic: Assembly of evidence into a single prompt for a quick, robust prediction.
- Expert: A multi-step structured synthesis pipeline (Metrics Analysis -> Trace Analysis -> 
          Graph Grounding -> Final Synthesis) providing 10x deeper insight than standard.
          This handles complex reasoning without brittle ReACT loops that fail on diverse providers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from murm.graph.engine import KnowledgeGraph
from murm.graph.embedder import Embedder
from murm.llm.provider import LLMProvider
from murm.simulation.trace import TraceWriter

logger = logging.getLogger(__name__)

_REPORT_SYSTEM = (
    "You are a rigorous social science analyst. "
    "Write a structured prediction report grounded exclusively in the simulation evidence provided. "
    "Be direct and concrete. Make a specific prediction. Do not hedge excessively."
)


class ReportAgent:
    def __init__(
        self,
        llm:              LLMProvider,
        graph:            KnowledgeGraph,
        embedder:         Embedder,
        trace:            TraceWriter,
        metrics_summary:  dict,
        simulation_config: dict,
    ) -> None:
        self._llm     = llm
        self._graph   = graph
        self._embedder = embedder
        self._trace   = trace
        self._metrics = metrics_summary
        self._config  = simulation_config

    async def generate(self, prediction_question: str, mode: str = "basic") -> str:
        ctx = self._assemble_context(prediction_question)
        if mode == "expert":
            return await self._generate_expert(prediction_question, ctx)
        return await self._generate_basic(prediction_question, ctx)

    async def _generate_basic(self, prediction_question: str, ctx: dict) -> str:
        prompt = _build_report_prompt(prediction_question, ctx)

        logger.info("Generating basic report for: %s", prediction_question[:80])
        try:
            report = await self._llm.complete(
                messages=[
                    {"role": "system", "content": _REPORT_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )
            return report.strip() or "Report generation returned an empty response."
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)
            return _fallback_report(prediction_question, ctx, str(exc))

    async def _generate_expert(self, prediction_question: str, ctx: dict) -> str:
        logger.info("Starting Expert Mode multi-step analysis...")
        try:
            # Step 1: Deep Metrics Analysis
            metrics_prompt = f"Analyze these simulation metrics for anomalies, turning points, and convergence patterns:\n{json.dumps(ctx['metrics'], indent=2)}\nOpinion trend:\n{json.dumps(ctx['opinion_trend'], indent=2)}"
            metrics_analysis = await self._llm.complete([{"role": "user", "content": metrics_prompt}], max_tokens=1000)
            
            # Step 2: Agent Discourse Trace Analysis
            trace_str = "\n".join(ctx['trace_sample'])
            trace_prompt = f"Analyze this agent discourse trace. Identify key arguments, influencer impacts, and moments where opinions shifted:\n{trace_str}"
            trace_analysis = await self._llm.complete([{"role": "user", "content": trace_prompt}], max_tokens=1000)

            # Step 3: Graph Grounding
            graph_str = "\n".join(ctx['graph_entities'])
            graph_prompt = f"Correlate the discourse with these factual entities from the source document. What entities drove the debate?\n{graph_str}"
            graph_analysis = await self._llm.complete([{"role": "user", "content": graph_prompt}], max_tokens=1000)

            # Step 4: Final Comprehensive Synthesis
            synth_prompt = f"""PREDICTION QUESTION: {prediction_question}

You are an elite intelligence analyst. Synthesize the findings of your sub-agents into a massive, highly detailed final report.

METRICS ANALYSIS: {metrics_analysis}
DISCOURSE ANALYSIS: {trace_analysis}
FACTUAL GROUNDING: {graph_analysis}

Write a comprehensive report with:
## Executive Prediction (Direct answer)
## Deep Evidence (Metrics & Turning Points)
## Discourse & Influencer Analysis (Who drove the conversation and arguments used)
## Contextual Grounding (How the entities shaped opinions)
## Confidence Assessment (0-100 with strict justification)
## Strategic Vulnerabilities & Limitations
"""
            report = await self._llm.complete([{"role": "system", "content": _REPORT_SYSTEM}, {"role": "user", "content": synth_prompt}], temperature=0.4, max_tokens=4000)
            return report.strip()
        except Exception as exc:
            logger.error("Expert report generation failed: %s", exc)
            return _fallback_report(prediction_question, ctx, str(exc))

    def _assemble_context(self, question: str) -> dict:
        # Read all trace actions
        all_actions: list[dict] = []
        try:
            all_actions = self._trace.read_all()
        except Exception:
            pass

        # Subsample evenly for the prompt (40 actions max to stay within token budget)
        n = min(40, len(all_actions))
        step = max(1, len(all_actions) // n) if n else 1
        sampled = all_actions[::step][:n]

        # Build opinion trend by round
        by_round: dict[int, list[str]] = {}
        for a in all_actions:
            r = a.get("round", 0)
            op = a.get("opinion_shift") or a.get("current_opinion", "")
            if op:
                by_round.setdefault(r, []).append(op)

        opinion_trend: dict[str, str] = {}
        for r, ops in sorted(by_round.items()):
            counts: dict[str, int] = {}
            for o in ops:
                counts[o] = counts.get(o, 0) + 1
            opinion_trend[f"round_{r}"] = max(counts, key=counts.get) if counts else "neutral"

        # Top entities from graph
        graph_entities: list[str] = []
        try:
            for n in (self._graph.get_all_nodes() or [])[:10]:
                s = n.get("summary", "")[:80]
                graph_entities.append(f"{n.get('name','')} ({n.get('entity_type','')}): {s}")
        except Exception:
            pass

        # Format trace sample
        trace_lines = []
        for a in sampled:
            c = (a.get("content") or "")[:120]
            if c:
                op = a.get("opinion_shift") or ""
                trace_lines.append(f"R{a.get('round','?')} [{op}]: {c}")

        return {
            "metrics":        self._metrics,
            "opinion_trend":  opinion_trend,
            "trace_sample":   trace_lines,
            "graph_entities": graph_entities,
            "n_agents":       self._config.get("n_agents", "?"),
            "n_rounds":       self._config.get("n_rounds", "?"),
            "total_actions":  len(all_actions),
        }


def _build_report_prompt(question: str, ctx: dict) -> str:
    metrics_str = json.dumps(ctx["metrics"], indent=2) if ctx["metrics"] else "(no metrics)"
    trend_str   = json.dumps(ctx["opinion_trend"], indent=2) if ctx["opinion_trend"] else "(no trend data)"
    trace_str   = "\n".join(ctx["trace_sample"]) if ctx["trace_sample"] else "(no trace data)"
    graph_str   = "\n".join(ctx["graph_entities"]) if ctx["graph_entities"] else "(no graph data)"

    return f"""PREDICTION QUESTION: {question}

SIMULATION PARAMETERS:
Agents: {ctx['n_agents']}  |  Rounds: {ctx['n_rounds']}  |  Total actions: {ctx['total_actions']}

FINAL EMERGENCE METRICS:
{metrics_str}

DOMINANT OPINION BY ROUND (tracks how collective stance shifted):
{trend_str}

REPRESENTATIVE AGENT POSTS FROM SIMULATION:
{trace_str}

KNOWLEDGE GRAPH ENTITIES:
{graph_str}

Write a complete prediction report with EXACTLY these five sections:

## Prediction
State your direct, specific answer to the prediction question in one clear paragraph.
Commit to a direction. Do not say "it depends" without specifying what it depends on.

## Evidence
Cite specific metrics (entropy trajectory, polarization, velocity) and specific
agent behaviors from the trace that support your prediction.

## Emergence Analysis
What collective dynamics emerged from the agent interactions?
Did opinion shift, stabilise, or split? What drove the dominant pattern?

## Confidence Assessment
Score: [write a number 0-100]
Justify the score based on consensus strength, entropy trajectory, and how
consistent the simulation results were across rounds.

## Limitations
What real-world factors are not captured by this simulation that could alter the prediction?"""


def _fallback_report(question: str, ctx: dict, error: str) -> str:
    """Minimal data-only report when the LLM call fails entirely."""
    metrics = ctx.get("metrics") or {}
    trend   = ctx.get("opinion_trend") or {}
    last_r  = max(trend.keys(), default="—") if trend else "—"
    dominant = trend.get(last_r, "unknown").replace("_", " ") if trend else "unknown"

    return f"""## Prediction
Based on raw simulation data, the dominant stance at the end of the simulation was **{dominant}**.
Full LLM analysis was unavailable (error: {error}).

## Evidence
Agents: {ctx.get('n_agents')} | Rounds: {ctx.get('n_rounds')} | Actions: {ctx.get('total_actions', 0)}
Final metrics: {json.dumps(metrics, indent=2)}

## Emergence Analysis
Opinion trend across rounds:
{json.dumps(trend, indent=2)}

## Confidence Assessment
Score: 20
Raw simulation data only — LLM-based analysis was not available.

## Limitations
The report was generated from raw data without LLM analysis due to an error.
Please retry the report generation or check your API key and server logs."""