"""
Calibration and uncertainty quantification.

MiroFish produces point-estimate predictions with no confidence bounds.
This module adds the statistical framework that makes the output research-grade.

Brier score: measures the accuracy of probabilistic predictions.
  - Lower is better; 0.0 is perfect, 0.25 is no-skill baseline for binary events.

Calibration curve: groups predictions by confidence bucket and checks
  whether claimed 70% confidence events actually happen ~70% of the time.

Sensitivity analysis: runs the same simulation N times with different random
  seeds and reports the variance in key outcomes, giving a distribution of
  predictions rather than a single trajectory.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PredictionRecord:
    """
    One logged prediction with its stated confidence and eventual ground truth.
    Ground truth is filled in after the real-world event resolves.
    """
    run_id: str
    prediction_question: str
    predicted_outcome: str
    confidence: float              # 0.0 – 1.0
    simulation_metrics: dict
    ground_truth: str | None = None
    ground_truth_match: bool | None = None
    brier_score: float | None = None


def compute_brier_score(confidence: float, outcome_occurred: bool) -> float:
    """
    Brier score for a single binary prediction.
    confidence: probability assigned to 'outcome_occurred = True'.
    Returns a value in [0, 1]; lower is better.
    """
    forecast = confidence
    observation = 1.0 if outcome_occurred else 0.0
    return (forecast - observation) ** 2


@dataclass
class SensitivityResult:
    """
    Outcome of running N simulation seeds and aggregating.
    """
    n_seeds: int
    seeds_used: list[int]
    dominant_opinions: list[str]          # plurality opinion per run
    final_entropies: list[float]
    polarization_indices: list[float]
    mean_final_entropy: float
    std_final_entropy: float
    mean_polarization: float
    std_polarization: float
    consensus_rate: float                 # fraction of runs where one opinion exceeded 50%
    prediction_variance: str              # "low" | "medium" | "high" based on std thresholds


def compute_sensitivity(metrics_per_run: list[dict]) -> SensitivityResult:
    """
    Aggregate metrics from multiple simulation runs (different seeds) to produce
    a sensitivity analysis result.

    metrics_per_run: list of final_summary() dicts from MetricsCollector,
                     one per seed run.
    """
    n = len(metrics_per_run)
    entropies = [m.get("final_entropy", 0.0) for m in metrics_per_run]
    polarizations = [m.get("polarization_index", 0.0) for m in metrics_per_run]
    dominant_opinions = [
        _mode_of_list(m.get("entropy_time_series", [])) for m in metrics_per_run
    ]

    mean_entropy = statistics.mean(entropies) if entropies else 0.0
    std_entropy = statistics.stdev(entropies) if len(entropies) > 1 else 0.0
    mean_pol = statistics.mean(polarizations) if polarizations else 0.0
    std_pol = statistics.stdev(polarizations) if len(polarizations) > 1 else 0.0

    # Consensus: entropy < log2(5)/2 implies one opinion holds > ~50% share
    consensus_count = sum(1 for e in entropies if e < math.log2(5) / 2)

    variance_label = _variance_label(std_entropy)

    return SensitivityResult(
        n_seeds=n,
        seeds_used=list(range(n)),
        dominant_opinions=dominant_opinions,
        final_entropies=entropies,
        polarization_indices=polarizations,
        mean_final_entropy=round(mean_entropy, 4),
        std_final_entropy=round(std_entropy, 4),
        mean_polarization=round(mean_pol, 4),
        std_polarization=round(std_pol, 4),
        consensus_rate=round(consensus_count / n, 3) if n > 0 else 0.0,
        prediction_variance=variance_label,
    )


def uncertainty_statement(sensitivity: SensitivityResult) -> str:
    """
    Produce a human-readable uncertainty statement for inclusion in reports.
    """
    variance_map = {
        "low": (
            f"Across {sensitivity.n_seeds} independent runs, outcomes were highly consistent "
            f"(entropy std={sensitivity.std_final_entropy:.3f}). "
            "The prediction is robust to random variation."
        ),
        "medium": (
            f"Across {sensitivity.n_seeds} independent runs, moderate variance was observed "
            f"(entropy std={sensitivity.std_final_entropy:.3f}). "
            "Treat the prediction as directionally reliable but not point-precise."
        ),
        "high": (
            f"Across {sensitivity.n_seeds} independent runs, outcomes varied substantially "
            f"(entropy std={sensitivity.std_final_entropy:.3f}). "
            "The simulation is sensitive to initial conditions. "
            "Multiple futures are plausible — interpret the prediction cautiously."
        ),
    }
    base = variance_map.get(sensitivity.prediction_variance, "")
    consensus_note = ""
    if sensitivity.consensus_rate > 0.7:
        consensus_note = (
            f" Consensus (one opinion > 50%) emerged in "
            f"{int(sensitivity.consensus_rate * sensitivity.n_seeds)} of {sensitivity.n_seeds} runs."
        )
    return base + consensus_note


# Internal

def _mode_of_list(values: list) -> Any:
    if not values:
        return None
    return max(set(values), key=values.count)


def _variance_label(std: float) -> str:
    if std < 0.05:
        return "low"
    if std < 0.15:
        return "medium"
    return "high"
