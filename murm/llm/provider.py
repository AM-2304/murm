"""
LiteLLM wrapper. Every component that needs an LLM calls this - never litellm directly.

Key design decisions:
  - complete_json() NEVER sends response_format to Groq. Groq silently hangs on
    that parameter for all its models. JSON is enforced through the prompt instead.
  - 60-second hard timeout on every call via asyncio.wait_for.
  - Exponential backoff with jitter, capped at 30s, for rate limit recovery.
  - AgentLLMProvider uses a separate, faster model for agent turns.
"""

from __future__ import annotations

import asyncio
import hashlib
import hashlib
import json
import logging
import random
from pathlib import Path
from pathlib import Path
from typing import Any

import litellm
from litellm import acompletion

from murm.config import settings
from murm.llm.budget import BudgetManager

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True
if settings.log_level.value != "DEBUG":
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)

_BASE_WAIT  = 2.0
_MAX_WAIT   = 30.0
_JITTER     = 0.5
_CALL_TIMEOUT = 60.0  # hard per-call timeout in seconds


class LLMProvider:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        budget: BudgetManager | None = None,
        max_retries: int = 4,
        retry_delay: float = _BASE_WAIT,
    ) -> None:
        self.model       = model or settings.llm_model
        self.api_key     = api_key or settings.llm_api_key
        self.base_url    = base_url or settings.llm_base_url
        self.budget      = budget
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        """
        Chat completion with retry and hard timeout.
        Does NOT accept response_format - callers that need JSON use complete_json().
        """
        call_kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        if self.api_key:  call_kwargs["api_key"]  = self.api_key
        if self.base_url: call_kwargs["base_url"] = self.base_url

        # -- DEMO MODE MOCK CACHING INTERCEPTOR --
        demo_mode = getattr(settings, "demo_mode", False)
        cache_file = None
        if demo_mode:
            cache_dir = Path("demo/cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            prompt_hash = hashlib.sha256(json.dumps([messages, self.model], sort_keys=True).encode()).hexdigest()
            cache_file = cache_dir / f"{prompt_hash}.json"
            
            if cache_file.exists():
                try:
                    await asyncio.sleep(0.3)  # Add realistic async latency for the UI stream
                    return json.loads(cache_file.read_text(encoding="utf-8"))["content"]
                except Exception as e:
                    logger.warning(f"Failed to read demo cache: {e}")
        # ---------------------



        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    acompletion(**call_kwargs),
                    timeout=_CALL_TIMEOUT,
                )
                content = response.choices[0].message.content or ""
                if self.budget and response.usage:
                    u = response.usage
                    self.budget.record(u.prompt_tokens, u.completion_tokens, self.model)
                
                # If demo mode is on but this prompt was uncached, save it forever
                if demo_mode and cache_file:
                    try:
                        cache_file.write_text(json.dumps({"content": content}), encoding="utf-8")
                    except Exception as e:
                        logger.error(f"Failed to write demo cache: {e}")
                
                return content

            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    raise RuntimeError("LLM call timed out after 60s on final retry")
                logger.warning("LLM timeout (attempt %d/%d) - retrying", attempt + 1, self.max_retries)
                await asyncio.sleep(self.retry_delay)

            except litellm.RateLimitError:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        "Rate limit persists after all retries. "
                        "On Groq paid tier this should not happen - check your API key."
                    )
                wait = min(
                    self.retry_delay * (2 ** attempt) + random.uniform(0, _JITTER),
                    _MAX_WAIT,
                )
                logger.warning("Rate limit (attempt %d/%d) - waiting %.0fs", attempt + 1, self.max_retries, wait)
                await asyncio.sleep(wait)

            except litellm.APIConnectionError as exc:
                if attempt == self.max_retries - 1:
                    raise
                wait = self.retry_delay + random.uniform(0, _JITTER)
                logger.warning("Connection error attempt %d: %s - retry in %.0fs", attempt + 1, exc, wait)
                await asyncio.sleep(wait)

        raise RuntimeError(f"LLM call failed after {self.max_retries} retries")

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict | list:
        """
        JSON-structured completion. Never sends response_format to the API
        because Groq silently hangs on that parameter. Instead injects the
        JSON requirement into the user message prompt directly.
        """
        msgs = list(messages)
        last = msgs[-1]
        # Append JSON instruction only if not already present
        if "json" not in last["content"].lower()[-80:]:
            msgs[-1] = {
                "role": last["role"],
                "content": last["content"].rstrip()
                    + "\n\nRespond with valid JSON only. No markdown fences, no preamble.",
            }
        raw = await self.complete(msgs, temperature, max_tokens)
        return _parse_json(raw)


class AgentLLMProvider(LLMProvider):
    """
    Faster, lighter model for per-agent turns inside the simulation loop.
    Fails fast (3 retries, 1s base) because a failed agent turn just skips
    that agent for the round - it does not break the simulation.
    """
    def __init__(self, budget: BudgetManager | None = None) -> None:
        super().__init__(
            model=settings.agent_model_resolved,
            api_key=settings.agent_api_key_resolved,
            base_url=settings.agent_base_url_resolved,
            budget=budget,
            max_retries=3,
            retry_delay=1.0,
        )


def _parse_json(raw: str) -> dict | list:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}\nRaw: {raw[:300]}") from exc
