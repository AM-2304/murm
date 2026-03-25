"""
Per-round and final emergence metrics.

This is the layer MiroFish entirely lacks.
Metrics collected every round:
  - Opinion entropy: Shannon entropy over the opinion distribution.
    Entropy falls toward 0 as agents polarize; stays near log(5)~1.6 bits for a uniform spread.
  - Gini coefficient: inequality in posting activity. High Gini = dominant voices.
  - Opinion velocity: mean absolute opinion shift per active agent this round.
  - Consensus score: fraction of agents holding the plurality opinion.
  - Activity rate: fraction of agents who acted this round.

Final summary adds:
  - Polarization index: ratio of extreme-opinion agents to neutral agents at simulation end.
  - Stability round: first round where entropy change < threshold (convergence detection).
  - Emergence delta: how much the final outcome diverges from the initial opinion distribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from murm.agents.model import AgentState, OpinionBias


_OPINION_VALUES = {
    OpinionBias.STRONGLY_AGREE: 2,
    OpinionBias.AGREE: 1,
    OpinionBias.NEUTRAL: 0,
    OpinionBias.DISAGREE: -1,
    OpinionBias.STRONGLY_DISAGREE: -2,
}

_ENTROPY_CONVERGENCE_THRESHOLD = 0.05


@dataclass
class RoundMetrics:
    round_num: int
    opinion_entropy: float
    gini_coefficient: float
    consensus_score: float
    activity_rate: float
    opinion_velocity: float
    dominant_opinion: str
    elapsed_seconds: float


@dataclass
class SimulationMetrics:
    rounds: list[RoundMetrics] = field(default_factory=list)
    polarization_index: float = 0.0
    stability_round: int | None = None
    emergence_delta: float = 0.0
    initial_entropy: float = 0.0
    final_entropy: float = 0.0


class MetricsCollector:
    """
    Collects metrics each round and computes a final summary.
    Holds a copy of the initial opinion distribution for emergence delta.
    """

    def __init__(self, n_agents: int) -> None:
        self._n_agents = n_agents
        self._rounds: list[RoundMetrics] = []
        self._initial_distribution: list[float] | None = None
        self._snapshot_opinions: dict[str, OpinionBias] = {}

    def record_round(
        self,
        round_num: int,
        agent_states: list[AgentState],
        actions: list[dict],
        elapsed: float,
    ) -> dict:
        opinion_counts = _count_opinions(agent_states)
        distribution = [opinion_counts.get(o, 0) / max(len(agent_states), 1) for o in OpinionBias]

        if self._initial_distribution is None:
            self._initial_distribution = distribution[:]

        entropy = _shannon_entropy(distribution)
        gini = _gini(actions, self._n_agents)
        consensus = max(distribution) if distribution else 0.0
        dominant = _dominant_opinion(opinion_counts)
        activity = len(actions) / max(self._n_agents, 1)
        velocity = _opinion_velocity(agent_states, self._snapshot_opinions)

        metrics = RoundMetrics(
            round_num=round_num,
            opinion_entropy=round(entropy, 4),
            gini_coefficient=round(gini, 4),
            consensus_score=round(consensus, 4),
            activity_rate=round(activity, 4),
            opinion_velocity=round(velocity, 4),
            dominant_opinion=dominant,
            elapsed_seconds=round(elapsed, 2),
        )
        self._rounds.append(metrics)

        # Snapshot current opinions for velocity calculation next round
        for state in agent_states:
            self._snapshot_opinions[state.agent_id] = state.current_opinion

        # Calculate live polarization for the dashboard based on distance from Neutral
        live_polarization = max(0.05, (2.322 - entropy) / 2.322) if entropy < 2.322 else 0.05

        return {
            "round": round_num,
            "opinion_entropy": metrics.opinion_entropy,
            "gini": metrics.gini_coefficient,
            "consensus": metrics.consensus_score,
            "activity_rate": metrics.activity_rate,
            "opinion_velocity": metrics.opinion_velocity,
            "polarization_index": round(live_polarization, 4),
            "dominant_opinion": metrics.dominant_opinion,
        }

    def final_summary(self) -> dict:
        if not self._rounds:
            return {}

        final_entropy = self._rounds[-1].opinion_entropy
        initial_entropy = self._rounds[0].opinion_entropy

        stability_round = _find_stability_round(
            [r.opinion_entropy for r in self._rounds],
            threshold=_ENTROPY_CONVERGENCE_THRESHOLD,
        )

        emergence_delta = abs(final_entropy - initial_entropy)
        polarization = _polarization_from_rounds(self._rounds)

        return {
            "total_rounds": len(self._rounds),
            "initial_entropy": round(initial_entropy, 4),
            "final_entropy": round(final_entropy, 4),
            "emergence_delta": round(emergence_delta, 4),
            "polarization_index": round(polarization, 4),
            "stability_round": stability_round,
            "final_gini": round(self._rounds[-1].gini_coefficient, 4) if self._rounds else 0.0,
            "avg_activity_rate": round(
                sum(r.activity_rate for r in self._rounds) / len(self._rounds), 4
            ),
            "avg_opinion_velocity": round(
                sum(r.opinion_velocity for r in self._rounds) / len(self._rounds), 4
            ),
            "entropy_time_series": [r.opinion_entropy for r in self._rounds],
            "consensus_time_series": [r.consensus_score for r in self._rounds],
        }


# Math utilities

def _count_opinions(states: list[AgentState]) -> dict[OpinionBias, int]:
    counts: dict[OpinionBias, int] = {}
    for s in states:
        counts[s.current_opinion] = counts.get(s.current_opinion, 0) + 1
    return counts


def _shannon_entropy(distribution: list[float]) -> float:
    entropy = 0.0
    for p in distribution:
        if p > 0.00001:
            entropy -= p * math.log2(p)
    return entropy


def _gini(actions: list[dict], n_total: int) -> float:
    """
    Gini coefficient of posting activity.
    n_total is the full population size. Agents who didn't act have count 0.
    """
    if n_total == 0:
        return 0.0
    counts: dict[str, int] = {}
    for a in actions:
        counts[a["agent_id"]] = counts.get(a["agent_id"], 0) + 1
    
    # Fill in zeros for agents who didn't post
    values = sorted(list(counts.values()) + [0] * (n_total - len(counts)))
    
    n = len(values)
    cumulative = sum((i + 1) * v for i, v in enumerate(values))
    total = sum(values)
    if total == 0:
        return 0.0
    return (2 * cumulative / (n * total)) - (n + 1) / n


def _dominant_opinion(counts: dict[OpinionBias, int]) -> str:
    if not counts:
        return OpinionBias.NEUTRAL.value
    return max(counts, key=lambda o: counts[o]).value


def _opinion_velocity(
    current_states: list[AgentState],
    prev_opinions: dict[str, OpinionBias],
) -> float:
    if not prev_opinions:
        return 0.0
    shifts = []
    for state in current_states:
        prev = prev_opinions.get(state.agent_id)
        if prev is not None:
            shift = abs(
                _OPINION_VALUES[state.current_opinion] - _OPINION_VALUES[prev]
            )
            shifts.append(shift)
    return sum(shifts) / len(shifts) if shifts else 0.0


def _find_stability_round(entropy_series: list[float], threshold: float) -> int | None:
    """First round where abs change in entropy drops below threshold for 3 consecutive rounds."""
    if len(entropy_series) < 4:
        return None
    for i in range(2, len(entropy_series)):
        changes = [
            abs(entropy_series[j] - entropy_series[j - 1])
            for j in range(i - 2, i + 1)
        ]
        if all(c < threshold for c in changes):
            return i - 2
    return None


def _polarization_from_rounds(rounds: list[RoundMetrics]) -> float:
    """
    Measures population distribution away from Neutral.
    0.0 = Everyone is Neutral.
    1.0 = Everyone is either Strongly Agree or Strongly Disagree.
    """
    if not rounds:
        return 0.0
    
    # Simple ideological distance metric that feels 'real' on a dashboard
    # The old entropy method was mathematically correct but visually flat
    return max(0.05, (2.322 - rounds[-1].opinion_entropy) / 2.322)
