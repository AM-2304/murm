"""
Token budget manager: tracks cumulative token spend per session and enforces
a hard limit. Also provides pre-flight cost estimation before expensive runs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_FALLBACK_INPUT_COST  = 0.30   # USD per 1M tokens: conservative mid-tier estimate
_FALLBACK_OUTPUT_COST = 0.60

# Per-model pricing table (USD per 1M tokens, input / output)
# Updated March 2026. LiteLLM is queried first; this is the fallback.
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    # Groq paid tier (USD per 1M tokens: current as of 2026)
    "groq/llama-3.1-8b-instant":      (0.05,  0.08),
    "groq/llama3-8b-8192":            (0.05,  0.08),
    "groq/llama-3.3-70b-versatile":   (0.59,  0.79),
    "groq/llama3-70b-8192":           (0.59,  0.79),
    "groq/llama-3.1-70b-versatile":   (0.59,  0.79),
    "groq/gemma2-9b-it":              (0.20,  0.20),
    "groq/llama-3.2-3b-preview":      (0.06,  0.06),
    # Gemini
    "gemini/gemini-2.0-flash":        (0.075, 0.30),
    "gemini/gemini-1.5-flash":        (0.075, 0.30),
    "gemini/gemini-1.5-pro":          (1.25,  5.00),
    # OpenAI
    "gpt-4o-mini":                    (0.15,  0.60),
    "gpt-4o":                         (2.50, 10.00),
    "gpt-3.5-turbo":                  (0.50,  1.50),
    # Anthropic
    "claude-3-5-haiku-20241022":      (0.80,  4.00),
    "claude-3-5-sonnet-20241022":     (3.00, 15.00),
    # OpenRouter free tier (zero cost, 20 rpm / 200 req/day limit)
    "openrouter/meta-llama/llama-3.3-70b-instruct:free":  (0.00, 0.00),
    "openrouter/meta-llama/llama-4-maverick:free":         (0.00, 0.00),
    "openrouter/meta-llama/llama-4-scout:free":            (0.00, 0.00),
    "openrouter/deepseek/deepseek-chat-v3-0324:free":      (0.00, 0.00),
    "openrouter/deepseek/deepseek-r1:free":                (0.00, 0.00),
    "openrouter/google/gemini-2.0-flash-exp:free":         (0.00, 0.00),
    "openrouter/google/gemma-3-27b-it:free":               (0.00, 0.00),
    "openrouter/qwen/qwq-32b:free":                        (0.00, 0.00),
    "openrouter/nvidia/llama-3.1-nemotron-ultra-253b-v1:free": (0.00, 0.00),
    # OpenRouter paid (per million tokens)
    "openrouter/meta-llama/llama-3.3-70b-instruct":        (0.12, 0.30),
    "openrouter/google/gemini-flash-1.5":                  (0.075, 0.30),
    "openrouter/deepseek/deepseek-chat":                   (0.14, 0.28),
    "openrouter/mistralai/mistral-small":                  (0.10, 0.30),
    # Ollama: local, zero cost
    "ollama/llama3.2":                (0.00,  0.00),
    "ollama/llama3":                  (0.00,  0.00),
    "ollama/mistral":                 (0.00,  0.00),
}

# Realistic token estimates per pipeline stage
# Based on empirical runs with the optimised prompt sizes
_TOKENS_PER_AGENT_TURN     = 180   # optimised prompt (~120 prompt + ~60 completion)
_TOKENS_GRAPH_EXTRACTION   = 3000  # ontology pass + entity pass combined
_TOKENS_AGENT_GENERATION   = 400   # per agent persona
_TOKENS_REPORT             = 8000  # ReACT loop including tool calls


@dataclass
class TokenUsage:
    prompt_tokens:     int   = 0
    completion_tokens: int   = 0
    estimated_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BudgetExceeded(Exception):
    pass


class BudgetManager:
    def __init__(self, budget_tokens: int = 0) -> None:
        self._budget  = budget_tokens
        self._usage   = TokenUsage()

    def record(self, prompt_tokens: int, completion_tokens: int, model: str) -> None:
        cost = _model_cost(prompt_tokens, completion_tokens, model)
        self._usage.prompt_tokens      += prompt_tokens
        self._usage.completion_tokens  += completion_tokens
        self._usage.estimated_cost_usd += cost
        if self._budget > 0 and self._usage.total_tokens > self._budget:
                raise BudgetExceeded(
                    f"Token budget of {self._budget:,} exceeded "
                    f"(used {self._usage.total_tokens:,}). "
                    "Increase TOKEN_BUDGET in .env or set to 0 for unlimited."
                )

    @staticmethod
    def estimate_simulation_cost(
        n_agents: int,
        n_rounds: int,
        n_seeds: int = 1,
        model: str | None = None,
    ) -> dict:
        """
        Realistic pre-flight estimate that accounts for all pipeline stages
        and uses per-model pricing rather than a hardcoded fallback.
        """
        from murm.config import settings
        m = model or settings.llm_model

        # Agent turns (simulation loop)
        agent_calls        = n_agents * n_rounds * n_seeds
        agent_prompt       = int(_TOKENS_PER_AGENT_TURN * 0.65) * agent_calls
        agent_completion   = int(_TOKENS_PER_AGENT_TURN * 0.35) * agent_calls

        # Graph extraction (once per project, not per seed)
        graph_prompt       = int(_TOKENS_GRAPH_EXTRACTION * 0.75)
        graph_completion   = int(_TOKENS_GRAPH_EXTRACTION * 0.25)

        # Agent persona generation (once)
        persona_prompt     = int(_TOKENS_AGENT_GENERATION * 0.7) * n_agents
        persona_completion = int(_TOKENS_AGENT_GENERATION * 0.3) * n_agents

        # Report generation (once per seed)
        report_prompt      = int(_TOKENS_REPORT * 0.8) * n_seeds
        report_completion  = int(_TOKENS_REPORT * 0.2) * n_seeds

        total_prompt     = agent_prompt + graph_prompt + persona_prompt + report_prompt
        total_completion = agent_completion + graph_completion + persona_completion + report_completion
        total_tokens     = total_prompt + total_completion
        total_cost       = _model_cost(total_prompt, total_completion, m)

        # Per-stage breakdown
        agent_cost   = _model_cost(agent_prompt, agent_completion, m)
        graph_cost   = _model_cost(graph_prompt, graph_completion, m)
        persona_cost = _model_cost(persona_prompt, persona_completion, m)
        report_cost  = _model_cost(report_prompt, report_completion, m)

        return {
            "model":                    m,
            "total_calls":              agent_calls,
            "estimated_total_tokens":   total_tokens,
            "estimated_prompt_tokens":  total_prompt,
            "estimated_completion_tokens": total_completion,
            "estimated_cost_usd":       round(total_cost, 4),
            "breakdown": {
                "agent_turns":  round(agent_cost,   4),
                "graph_build":  round(graph_cost,   4),
                "personas":     round(persona_cost, 4),
                "report":       round(report_cost,  4),
            },
            "note": "Estimate. Actual cost depends on content length and model response size.",
        }

    @property
    def usage(self) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self._usage.prompt_tokens,
            completion_tokens=self._usage.completion_tokens,
            estimated_cost_usd=self._usage.estimated_cost_usd,
        )

    def snapshot(self) -> dict:
        u = self.usage
        return {
            "prompt_tokens":       u.prompt_tokens,
            "completion_tokens":   u.completion_tokens,
            "total_tokens":        u.total_tokens,
            "estimated_cost_usd":  round(u.estimated_cost_usd, 4),
            "budget_tokens":       self._budget,
            "budget_used_pct": (
                round(u.total_tokens / self._budget * 100, 1) if self._budget > 0 else None
            ),
        }

    def reset(self) -> None:
        self._usage = TokenUsage()



# Pricing helpers


def _model_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    # Try LiteLLM's live pricing database first
    try:
        import litellm
        cost = litellm.completion_cost(
            completion_response={
                "usage": {
                    "prompt_tokens":     prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens":      prompt_tokens + completion_tokens,
                }
            },
            model=model,
        )
        if cost is not None and cost > 0:
            return float(cost)
    except Exception:
        pass

    # Fall back to our own pricing table
    key = model.lower().strip()
    if key in _MODEL_PRICES:
        inp, out = _MODEL_PRICES[key]
        return (prompt_tokens * inp + completion_tokens * out) / 1_000_000

    # Unknown model: use conservative mid-tier estimate
    logger.debug("No pricing data for model '%s', using fallback", model)
    return (
        prompt_tokens     * _FALLBACK_INPUT_COST  / 1_000_000 +
        completion_tokens * _FALLBACK_OUTPUT_COST / 1_000_000
    )