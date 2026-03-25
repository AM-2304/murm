"""
Core simulation engine.

Architecture compared to MiroFish:
  - Fully async — no subprocess spawning, no file-based IPC
  - Plain-text agent responses accepted natively (no JSON mode required)
  - 60-second hard timeout per LLM call prevents infinite hangs
  - Environment is an abstract interface — forum, town hall, or custom
  - asyncio.Queue for real-time SSE streaming to the API layer
  - Seeded RNG throughout for reproducibility
  - Per-round emergence metrics collected automatically
  - God-view counterfactual event injection at any specified round
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from murm.agents.model import AgentProfile, AgentState, OpinionBias
from murm.llm.budget import BudgetManager
from murm.llm.provider import AgentLLMProvider
from murm.simulation.environment import Environment
from murm.simulation.metrics import MetricsCollector
from murm.simulation.trace import TraceWriter
from murm.simulation.web import fetch_real_world_context

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


@dataclass
class SimulationConfig:
    n_rounds:              int  = 10
    seed:                  int  = 42
    max_concurrent_agents: int  = 5      # paid Groq: 5 concurrent is safe and fast
    counterfactual_events: list[dict] = field(default_factory=list)
    environment_type:      str  = "forum"
    scenario_description:  str  = ""
    prediction_question:   str  = ""


@dataclass
class SimulationRun:
    run_id:        str
    config:        SimulationConfig
    status:        SimulationStatus = SimulationStatus.PENDING
    current_round: int              = 0
    total_actions: int              = 0
    error:         str | None       = None
    started_at:    float | None     = None
    completed_at:  float | None     = None


class SimulationEngine:
    """
    Drives a complete multi-round multi-agent simulation.
    Instantiate once per run, call execute(), read events from event_queue.
    """

    def __init__(
        self,
        run_id:        str,
        agents:        list[AgentProfile],
        environment:   Environment,
        config:        SimulationConfig,
        trace_dir:     Path,
        budget:        BudgetManager | None = None,
        event_queue:   asyncio.Queue | None = None,
        embedder=None,
    ) -> None:
        self._run_id   = run_id
        self._agents   = agents
        self._env      = environment
        self._config   = config
        self._trace    = TraceWriter(trace_dir / "trace.jsonl")
        self._budget   = budget
        self._embedder = embedder
        self._q        = event_queue or asyncio.Queue(maxsize=2000)

        self._llm      = AgentLLMProvider(budget=budget)
        self._metrics  = MetricsCollector(len(agents))
        self._states   = {
            p.agent_id: AgentState(agent_id=p.agent_id, current_opinion=p.opinion_bias)
            for p in agents
        }
        self._rng       = random.Random(config.seed)
        self._sem       = asyncio.Semaphore(config.max_concurrent_agents)
        self._cancelled = False
        self._run       = SimulationRun(run_id=run_id, config=config)

    async def execute(self) -> SimulationRun:
        self._run.status     = SimulationStatus.RUNNING
        self._run.started_at = time.time()
        await self._emit("simulation_started", {
            "run_id":   self._run_id,
            "n_agents": len(self._agents),
        })

        try:
            # Fetch real world data context to ground the simulation, matching MiroFish real-time data functionality!
            try:
                real_world_ctx = await fetch_real_world_context(self._config.prediction_question)
                if real_world_ctx:
                    await self._inject_event(0, {
                        "content": real_world_ctx,
                        "source": "Real-World Web Search"
                    })
            except Exception as e:
                logger.debug("Initial web search failed: %s", e)

            for round_num in range(1, self._config.n_rounds + 1):
                if self._cancelled:
                    self._run.status = SimulationStatus.CANCELLED
                    break

                # Ongoing Data Fusion: Fetch new context every 3 rounds to keep simulation grounded in reality
                # This makes MURM a "Digital Twin of Public Opinion" that evolves with external info.
                if round_num > 1 and round_num % 3 == 0:
                    try:
                        # Use slightly varied queries or just refresh the same search for updates
                        refresh_ctx = await fetch_real_world_context(self._config.prediction_question)
                        if refresh_ctx:
                            await self._inject_event(round_num, {
                                "content": f"LATEST UPDATE: {refresh_ctx}",
                                "source": "Real-Time Intelligence Fusion"
                            })
                    except Exception as e:
                        logger.debug("Ongoing web search failed at round %d: %s", round_num, e)

                await self._run_round(round_num)
                for event in self._config.counterfactual_events:
                    if event.get("round") == round_num:
                        await self._inject_event(round_num, event)

            if self._run.status == SimulationStatus.RUNNING:
                self._run.status = SimulationStatus.COMPLETED

        except Exception as exc:
            logger.exception("Simulation %s failed at round %d", self._run_id, self._run.current_round)
            self._run.status = SimulationStatus.FAILED
            self._run.error  = str(exc)
            await self._emit("simulation_failed", {"error": str(exc)})

        finally:
            self._run.completed_at = time.time()
            self._trace.flush()
            await self._emit("simulation_ended", {
                "status":        self._run.status.value,
                "total_actions": self._run.total_actions,
                "rounds":        self._run.current_round,
                "metrics":       self._metrics.final_summary(),
            })

        return self._run

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def event_queue(self) -> asyncio.Queue:
        return self._q

    async def _run_round(self, round_num: int) -> None:
        self._run.current_round = round_num
        t0 = time.time()

        acting = [p for p in self._agents if self._rng.random() < p.reaction_speed]
        if not acting:
            acting = [self._rng.choice(self._agents)]

        # Try to get personalized feed if environment supports it, else global feed
        try:
            tasks = [self._agent_turn(p, round_num, self._env.get_context_feed(round_num, max_items=8, agent_id=p.agent_id)) for p in acting]
        except TypeError:
            feed = self._env.get_context_feed(round_num, max_items=8)
            tasks = [self._agent_turn(p, round_num, feed) for p in acting]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid: list[dict] = []
        for r in results:
            if isinstance(r, Exception):
                logger.debug("Agent turn exception: %s", r)
            elif r:
                valid.append(r)
                self._env.ingest_action(r)
                self._trace.write(r)
                self._run.total_actions += 1

        metrics = self._metrics.record_round(
            round_num=round_num,
            agent_states=list(self._states.values()),
            actions=valid,
            elapsed=time.time() - t0,
        )

        # Include up to 5 sample actions in the SSE event so the frontend live feed works
        samples = [
            {
                "agent_id":    a.get("agent_id", ""),
                "round":       a.get("round", round_num),
                "action_type": a.get("action_type", "post"),
                "content":     a.get("content", "")[:200],
                "opinion_shift": a.get("opinion_shift"),
            }
            for a in valid[:5] if a.get("content")
        ]
        # Derive live polarization from per-round entropy so the dashboard card updates each round.
        # Uses the same formula as MetricsCollector.final_summary(): (max_entropy - entropy) / max_entropy
        import math as _math
        _max_entropy = _math.log2(5)   # 5 opinion categories
        _entropy = metrics.get("opinion_entropy", 0) or 0
        live_polarization = max(0.0, round((_max_entropy - _entropy) / _max_entropy, 4))
        metrics_with_polarization = {**metrics, "polarization_index": live_polarization}

        await self._emit("round_completed", {
            "round":          round_num,
            "acting_agents":  len(acting),
            "actions":        len(valid),
            "metrics":        metrics_with_polarization,
            "budget":         self._budget.snapshot() if self._budget else None,
            "sample_actions": samples,
        })

    async def _agent_turn(
        self,
        profile: AgentProfile,
        round_num: int,
        feed: list[str],
    ) -> dict | None:
        async with self._sem:
            state = self._states[profile.agent_id]
            state.current_round = round_num

            # Optional RAG: inject relevant graph facts into the prompt
            graph_ctx: list[str] = []
            if self._embedder and state.last_action_summary:
                try:
                    hits = self._embedder.query(state.last_action_summary, top_k=2)
                    graph_ctx = [h["text"] for h in hits if h.get("distance", 1.0) < 0.85]
                except Exception:
                    pass

            prompt = _build_action_prompt(profile, state, feed, round_num, graph_ctx=graph_ctx)
            try:
                raw = await self._llm.complete(
                    messages=[
                        {"role": "system", "content": _AGENT_SYSTEM},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.85,
                    max_tokens=300,
                )
            except Exception as exc:
                logger.debug("Agent turn failed for %s: %s", profile.agent_id, exc)
                return None

            action = _parse_action(raw, profile.agent_id, round_num)
            if action:
                state.posts_made += 1
                state.last_action_summary = action.get("content", "")[:120]
                shift = action.get("opinion_shift")
                if shift:
                    try:
                        state.shift_opinion(OpinionBias(shift))
                    except ValueError:
                        pass
            return action

    async def _inject_event(self, round_num: int, event: dict) -> None:
        logger.info("Injecting event at round %d: %s", round_num, event.get("content", "")[:60])
        self._env.inject_external_event(
            content=event.get("content", ""),
            source=event.get("source", "external"),
            round_num=round_num,
        )
        await self._emit("event_injected", {
            "round":   round_num,
            "content": event.get("content", ""),
            "source":  event.get("source", "external"),
        })

    async def _emit(self, event_type: str, payload: dict) -> None:
        try:
            self._q.put_nowait({
                "type":      event_type,
                "timestamp": time.time(),
                "payload":   payload,
            })
        except asyncio.QueueFull:
            logger.debug("Event queue full — dropping %s", event_type)


# Agent system prompt — does NOT require JSON.
# _parse_action() handles both JSON and plain text responses.
_AGENT_SYSTEM = (
    "You are a social media user with a specific perspective. "
    "Write a short post (1-3 sentences) reacting to the recent discussion. "
    "Stay in character. If you have nothing to say this round, write only: abstain"
)


def _build_action_prompt(
    profile: AgentProfile,
    state:   AgentState,
    feed:    list[str],
    round_num: int,
    graph_ctx: list[str] | None = None,
    graph_context: list[str] | None = None,  # alias for test compatibility
) -> str:
    # Support both keyword argument names
    ctx = graph_context if graph_context is not None else (graph_ctx or [])
    feed_text = " | ".join(item[:100] for item in feed[-4:]) if feed else "No posts yet."
    ctx_text  = f" Context: {ctx[0][:100]}" if ctx else ""
    return (
        f"You are {profile.name}, {profile.occupation}, age {profile.age}."
        f" Current stance: {state.current_opinion.value.replace('_', ' ')}."
        f"{ctx_text}\n"
        f"Recent community posts (round {round_num}): {feed_text}\n"
        f"Write your post."
    )


def _parse_action(raw: str, agent_id: str, round_num: int) -> dict | None:
    """
    Accepts two response formats from the LLM:
      1. JSON:  {"action":"post","content":"...","opinion_shift":"..."}
      2. Plain text: treated as post content directly

    This dual-format approach is necessary because Groq (and most providers)
    return plain text when not using response_format, which we deliberately
    avoid sending since it causes silent hangs.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()

    # Try JSON first — supports rich action metadata
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if data.get("action") == "abstain":
                return None
            content = str(data.get("content", "")).strip()
            if not content:
                return None
            return {
                "agent_id":     agent_id,
                "round":        round_num,
                "action_type":  data.get("action", "post"),
                "content":      content,
                "opinion_shift": data.get("opinion_shift"),
                "timestamp":    time.time(),
            }
        except json.JSONDecodeError:
            pass

    # Plain text fallback — what Groq actually returns in practice
    skip = ("i abstain", "abstain", "no action", "i have nothing")
    if any(text.lower().startswith(s) for s in skip):
        return None

    return {
        "agent_id":     agent_id,
        "round":        round_num,
        "action_type":  "post",
        "content":      text[:400],
        "opinion_shift": None,
        "timestamp":    time.time(),
    }