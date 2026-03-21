"""
Report generation agent.

Design decision: this replaces the ReACT loop with a single structured LLM call.
The ReACT approach (MiroFish's design) failed on Groq because:
  1. It sent response_format=json_object which Groq doesn't support
  2. Each iteration was a separate LLM call — 12 iterations = 12 hang opportunities
  3. Tool-calling syntax varies by provider and breaks silently

Instead, we assemble all evidence locally (trace, metrics, graph entities) and
inject it directly into one prompt. The LLM writes the full report in one pass.
This is faster, cheaper, provider-agnostic, and more reliable.

The tradeoff: the report cannot dynamically query the graph the way ReACT can.
We compensate by pre-loading rich context before the call.
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

    async def generate(self, prediction_question: str) -> str:
        ctx    = self._assemble_context(prediction_question)
        prompt = _build_report_prompt(prediction_question, ctx)

        logger.info("Generating report for: %s", prediction_question[:80])
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