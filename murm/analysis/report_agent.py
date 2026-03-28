"""
Report generation agent — Analytical-grade intelligence reports.

Two modes:
- Basic: Single-prompt structured prediction.
- Expert: Multi-step synthesis pipeline (Metrics → Discourse → Graph → Synthesis)
  producing numbered-section intelligence briefs with cited evidence.

Report style: Numbered findings (01, 02, 03...), evidence blockquotes,
academic tone, no emojis, no markdown bold. Clean, minimalist, yet deeply analytical.
"""

from __future__ import annotations

import itertools
import json
import logging
from pathlib import Path

from murm.graph.engine import KnowledgeGraph
from murm.graph.embedder import Embedder
from murm.llm.provider import LLMProvider
from murm.simulation.trace import TraceWriter

logger = logging.getLogger(__name__)

# ─── System Prompt ───────────────────────────────────────────────────────────

_REPORT_SYSTEM = (
    "You are an elite intelligence analyst producing structured prediction reports. "
    "Your reports follow the style of professional policy analysis and social science intelligence briefs.\n\n"
    "ABSOLUTE RULES:\n"
    "1. NEVER use any emojis, emoticons, or unicode decorators.\n"
    "2. NEVER use markdown bold (**text**) or italics (*text*) or headers with more than two # marks.\n"
    "3. Use numbered section prefixes (01, 02, 03) for major findings.\n"
    "4. When citing specific agent discourse or simulated posts, wrap them in blockquotes (> lines).\n"
    "5. Write in precise, academic prose. No filler, no hedging, no AI cliches.\n"
    "6. Section titles must be DECLARATIVE FINDINGS, not questions.\n"
    "7. Keep the report between 6-8 focused sections. Quality over quantity.\n"
    "8. Start with an assertive, specific title that states your core prediction — not the question restated."
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

    # ─── Basic Mode ──────────────────────────────────────────────────────

    async def _generate_basic(self, prediction_question: str, ctx: dict) -> str:
        prompt = _build_report_prompt(prediction_question, ctx)

        logger.info("Generating basic report for: %s", str(prediction_question)[0:80])
        try:
            report = await self._llm.complete(
                messages=[
                    {"role": "system", "content": _REPORT_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3500,
            )
            return str(report).strip() or "Report generation returned an empty response."
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)
            return _fallback_report(prediction_question, ctx, str(exc))

    # ─── Expert Mode (Multi-Step Synthesis) ──────────────────────────────

    async def _generate_expert(self, prediction_question: str, ctx: dict) -> str:
        injection_summary = "\n".join(ctx.get('injections', [])) or "None (Baseline Run)"

        try:
            # Step 1: Deep Metrics Analysis
            metrics_prompt = (
                "Analyze these simulation metrics for anomalies, turning points, "
                "convergence patterns, and inflection moments. Identify which rounds "
                "showed the most volatile shifts and why.\n"
                f"Metrics:\n{json.dumps(ctx['metrics'], indent=2)}\n"
                f"Opinion trend by round:\n{json.dumps(ctx['opinion_trend'], indent=2)}"
            )
            metrics_analysis = await self._llm.complete(
                [{"role": "user", "content": metrics_prompt}], max_tokens=1200
            )

            # Step 2: Agent Discourse Trace Analysis
            trace_str = "\n".join(ctx['trace_sample'])
            trace_prompt = (
                "Analyze this agent discourse trace from a social simulation. "
                "Identify: (a) the 3 most influential arguments that shifted opinions, "
                "(b) specific turning point moments, (c) echo chamber formation or breaking, "
                "(d) the memetic spread pattern of dominant narratives.\n"
                "Cite specific agent posts as evidence using blockquotes.\n"
                f"Trace:\n{trace_str}"
            )
            trace_analysis = await self._llm.complete(
                [{"role": "user", "content": trace_prompt}], max_tokens=1200
            )

            # Step 3: Graph Grounding
            graph_str = "\n".join(ctx['graph_entities'])
            graph_prompt = (
                "Correlate the simulation discourse with these factual entities "
                "extracted from the source document. Which entities acted as catalysts? "
                "Which were ignored despite their importance? How did factual grounding "
                "shape opinion trajectories?\n"
                f"Entities:\n{graph_str}"
            )
            graph_analysis = await self._llm.complete(
                [{"role": "user", "content": graph_prompt}], max_tokens=1000
            )

            # Step 4: Final Comprehensive Synthesis
            synth_prompt = f"""PREDICTION QUESTION: {prediction_question}

You are drafting a professional intelligence prediction report. Synthesize the findings below into a structured report that follows the MiroFish intelligence brief format.

SUB-ANALYSIS INPUTS:
Metrics Analysis: {str(metrics_analysis)}
Discourse Analysis: {str(trace_analysis)}
Factual Grounding: {str(graph_analysis)}
Intervention Log: {injection_summary}
Simulation Parameters: {ctx['n_agents']} agents, {ctx['n_rounds']} rounds, {ctx['total_actions']} total actions
Raw Metrics for Dashboard: {json.dumps(ctx['metrics'], indent=2)}

REPORT STRUCTURE (follow this exactly):

# [Write an assertive title that states your core prediction as a declarative finding]

## Executive Intelligence Summary
Write 2-3 dense paragraphs providing your direct, confident answer to the prediction question. State the outcome, the confidence level, and the primary mechanism that drove the result. This section alone should give a busy reader everything they need.

## 01: [Primary Finding: Write a declarative title about the core opinion trajectory]
Explain the dominant opinion shift using metrics (entropy, polarization, velocity). Ground your analysis in specific numbers. Cite 1-2 specific agent posts as blockquote evidence. Conclude with the structural mechanism that produced this outcome.

## 02: [Secondary Finding: Write a declarative title about discourse dynamics and influence]
Who drove the debate? What arguments gained traction? When did the major turning points occur? Cite specific agent posts. Analyze the memetic spread of dominant narratives and whether echo chambers formed or broke.

## 03: [Tertiary Finding: Write a declarative title about real-world grounding impact]
How did the factual entities from the knowledge graph shape agent behavior? Which real-world facts acted as anchors? Were any critical facts ignored? Connect the simulation dynamics back to the real world.

## 04: [Intervention Resilience Analysis]
If any God Mode interventions or counterfactual events were injected, analyze how the population responded. Was consensus fragile or robust? How quickly did the group adapt to external shocks? If no interventions occurred, analyze the natural resilience of the emergent consensus.

## Quantitative Dashboard
Present the EXACT raw numbers from 'Raw Metrics for Dashboard' below. DO NOT guess or hallucinate these values.
- Opinion Entropy: [entropy value from raw metrics] : [1-sentence interpretation]
- Polarization Index: [polarization value from raw metrics] : [1-sentence interpretation]  
- Opinion Velocity: [velocity value from raw metrics] : [1-sentence interpretation]
- Consensus Strength: [consensus value from raw metrics] : [1-sentence interpretation]
- Total Opinion Shifts: [total_shifts value from raw metrics]

## Strategic Outlook and Confidence
Confidence Score: [0-100]
Write a rigorous justification for this score. Outline the top 3 limitations of the simulation. Identify the specific real-world factors, irrational behaviors, or exogenous shocks not captured that could alter this prediction. End with 2-3 concrete, actionable recommendations for stakeholders.
"""
            report = await self._llm.complete(
                [{"role": "system", "content": _REPORT_SYSTEM},
                 {"role": "user", "content": synth_prompt}],
                temperature=0.35,
                max_tokens=4500,
            )
            return str(report).strip()
        except Exception as exc:
            logger.error("Expert report generation failed: %s", exc)
            return _fallback_report(prediction_question, ctx, str(exc))

    # Context Assembly

    def _assemble_context(self, question: str) -> dict:
        # Read all trace actions
        all_actions: list[dict] = []
        try:
            all_actions = self._trace.read_all()
        except Exception:
            pass

        # Subsample evenly for the prompt (50 actions max for richer evidence)
        n = min(50, len(all_actions))
        step = max(1, len(all_actions) // n) if n else 1
        sampled_indices = list(range(0, len(all_actions), step))
        sampled = [all_actions[i] for i in list(itertools.islice(sampled_indices, n))]

        # Build opinion trend by round
        by_round: dict[int, list[str]] = {}
        for a in all_actions:
            r = a.get("round", 0)
            op = a.get("opinion_shift") or a.get("current_opinion", "")
            if op:
                by_round.setdefault(r, []).append(str(op))

        opinion_trend: dict[str, str] = {}
        for r, ops in sorted(by_round.items()):
            counts: dict[str, int] = {}
            for o in ops:
                counts[o] = counts.get(o, 0) + 1
            opinion_trend[f"round_{r}"] = max(counts, key=lambda k: counts[k]) if counts else "neutral"

        # Top entities from graph
        graph_entities: list[str] = []
        try:
            entities = self._graph.entities() or []
            for node in list(itertools.islice(entities, 12)):
                s = str(node.get("summary", ""))[0:100]
                graph_entities.append(
                    f"{node.get('name', '')} ({node.get('entity_type', '')}): {s}"
                )
        except Exception:
            pass

        # Format trace sample with richer context
        trace_lines = []
        for a in sampled:
            content = str(a.get("content") or "")[0:150]
            if content:
                op = a.get("opinion_shift") or ""
                agent = a.get("agent_id", "?")[0:8]
                trace_lines.append(
                    f"Round {a.get('round', '?')} | Agent {agent} [{op}]: {content}"
                )

        # Identify injections (God Mode)
        injections = []
        for a in all_actions:
            if a.get("action_type") == "external_event" or a.get("author_id") == "GodMode":
                injections.append(f"Round {a.get('round')}: {a.get('content')}")

        return {
            "metrics":        self._metrics,
            "opinion_trend":  opinion_trend,
            "trace_sample":   trace_lines,
            "graph_entities": graph_entities,
            "injections":     injections,
            "n_agents":       self._config.get("n_agents", "?"),
            "n_rounds":       self._config.get("n_rounds", "?"),
            "total_actions":  len(all_actions),
        }


# Prompt Builders

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

DOMINANT OPINION BY ROUND:
{trend_str}

REPRESENTATIVE AGENT DISCOURSE:
{trace_str}

KNOWLEDGE GRAPH ENTITIES:
{graph_str}

Write a structured intelligence prediction report following this format exactly:

# [Assertive prediction title - state your finding, not the question]

## Executive Intelligence Summary
2-3 paragraphs. Direct answer. Core trajectory. Primary mechanism.

## 01: [Primary Finding: declarative title about the core opinion shift]
Detailed analysis with metrics. Cite agent posts in blockquotes. Explain the mechanism.

## 02: [Secondary Finding: declarative title about discourse dynamics]
Influential arguments. Turning points. Echo chamber analysis.

## 03: [Tertiary Finding: declarative title about contextual grounding]
Entity impact. Real-world anchoring. Factual basis of the debate.

## Quantitative Dashboard
- Opinion Entropy: [value] : [interpretation]
- Polarization Index: [value] : [interpretation]
- Opinion Velocity: [value] : [interpretation]

## Strategic Outlook and Confidence
Score: [0-100]
Justified rigorously. Top 3 limitations. Actionable recommendations."""


def _fallback_report(question: str, ctx: dict, error: str) -> str:
    """Minimal data-only report when the LLM call fails entirely."""
    metrics = ctx.get("metrics") or {}
    trend   = ctx.get("opinion_trend") or {}
    last_r  = max(trend.keys(), default="--") if trend else "--"
    dominant = str(trend.get(last_r, "unknown")).replace("_", " ") if trend else "unknown"

    return f"""# Simulation Data Summary (LLM Unavailable)

## Executive Intelligence Summary
Based on raw simulation data, the dominant stance at the end of the simulation was {dominant}.
Full LLM-powered analysis was unavailable due to: {error}

## 01 -- Raw Metrics
Agents: {ctx.get('n_agents')} | Rounds: {ctx.get('n_rounds')} | Actions: {ctx.get('total_actions', 0)}
{json.dumps(metrics, indent=2)}

## 02 -- Opinion Trend
{json.dumps(trend, indent=2)}

## Strategic Outlook and Confidence
Score: 15
This report contains raw data only. LLM analysis was not available.
Retry report generation or check API configuration."""