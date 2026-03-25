"""
Generates a demographically and ideologically diverse agent population.

The core problem this solves: if you ask an LLM to "generate 50 agents" in one
shot it produces a homogeneous cluster. Instead MURM uses a seeded quota system:
  - Opinion distribution is computed before any LLM call (deterministic)
  - Influence role distribution mirrors empirical social network topology
  - Each agent is generated individually with its assignment visible to the LLM
  - All agents are generated concurrently in batches of 5 for speed
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import uuid
from typing import Literal

from murm.agents.model import AgentProfile, InfluenceRole, OpinionBias
from murm.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

OpinionDist = Literal["normal", "bimodal", "power_law", "uniform"]

# Real social network participation topology
_INFLUENCE_ROLE_WEIGHTS = {
    InfluenceRole.INFLUENCER:   0.05,
    InfluenceRole.ACTIVE_USER:  0.25,
    InfluenceRole.PASSIVE_USER: 0.55,
    InfluenceRole.SKEPTIC:      0.10,
    InfluenceRole.AMPLIFIER:    0.05,
}

_OPINION_DISTRIBUTIONS: dict[str, list[float]] = {
    "normal":    [0.05, 0.20, 0.50, 0.20, 0.05],
    "bimodal":   [0.25, 0.20, 0.10, 0.20, 0.25],
    "power_law": [0.45, 0.25, 0.15, 0.10, 0.05],
    "uniform":   [0.20, 0.20, 0.20, 0.20, 0.20],
}

_OPINION_ORDER = [
    OpinionBias.STRONGLY_AGREE,
    OpinionBias.AGREE,
    OpinionBias.NEUTRAL,
    OpinionBias.DISAGREE,
    OpinionBias.STRONGLY_DISAGREE,
]

# Note: no JSON fences instruction needed here — complete_json() appends it automatically
_PERSONA_SYSTEM = """You are a social scientist creating realistic simulation personas.
Generate exactly ONE person profile. The person must fit the assigned opinion and role.
Return ONLY a JSON object with these exact keys:
name (full name string), age (integer 18-75), occupation (specific job title string),
background (2 sentence string of life context relevant to the topic),
communication_style (one of: formal casual sarcastic empathetic aggressive analytical),
expertise_domains (list of 2 strings), trusted_sources (list of 2 strings),
reaction_speed (float 0.1-1.0), susceptibility (float 0.1-1.0)"""


class PersonaGenerator:
    def __init__(self, llm: LLMProvider, seed: int = 42) -> None:
        self._llm = llm
        self._rng = random.Random(seed)

    async def generate_population(
        self,
        n_agents: int,
        topic: str,
        context: str = "",
        opinion_dist: OpinionDist = "normal",
        institutions: list[dict] | None = None,
    ) -> list[AgentProfile]:
        assignments = self._compute_assignments(n_agents, opinion_dist)
        logger.info(
            "Generating %d agents, distribution=%s",
            n_agents, opinion_dist,
        )

        # Generate in concurrent batches of 5 — faster than sequential,
        # safe on paid Groq tier (6000 rpm limit, 5 concurrent = trivial load)
        # If institutions are provided, assign some agents to represent them
        institution_list = institutions or []
        n_inst = min(len(institution_list), max(1, n_agents // 10))
        
        for i in range(n_agents):
            opinion, role = assignments[i]
            inst = institution_list[i % len(institution_list)] if i < n_inst else None
            
            tasks.append(
                self._generate_one(
                    i, topic, context, opinion, role,
                    demographic_seed=inst["name"] if inst else self._rng.choice(archetypes),
                    is_institution=bool(inst),
                    inst_summary=inst.get("summary", "") if inst else ""
                )
            )
            
            if len(tasks) >= BATCH:
                batch_profiles = await asyncio.gather(*tasks, return_exceptions=False)
                profiles.extend(batch_profiles)
                tasks = []
                logger.info("Generated agents up to %d / %d", len(profiles), n_agents)

        if tasks:
            batch_profiles = await asyncio.gather(*tasks, return_exceptions=False)
            profiles.extend(batch_profiles)

        return profiles

    def _compute_assignments(
        self, n_agents: int, opinion_dist: OpinionDist
    ) -> list[tuple[OpinionBias, InfluenceRole]]:
        opinion_weights = _OPINION_DISTRIBUTIONS[opinion_dist]
        opinion_counts  = _quota_round(n_agents, opinion_weights)
        role_weights    = list(_INFLUENCE_ROLE_WEIGHTS.values())
        role_counts     = _quota_round(n_agents, role_weights)

        opinions: list[OpinionBias] = []
        for opinion, count in zip(_OPINION_ORDER, opinion_counts):
            opinions.extend([opinion] * count)

        roles: list[InfluenceRole] = []
        for role, count in zip(list(_INFLUENCE_ROLE_WEIGHTS.keys()), role_counts):
            roles.extend([role] * count)

        self._rng.shuffle(opinions)
        self._rng.shuffle(roles)
        return list(zip(opinions, roles))

    async def _generate_one(
        self,
        index: int,
        topic: str,
        context: str,
        opinion: OpinionBias,
        role: InfluenceRole,
        demographic_seed: str,
        is_institution: bool = False,
        inst_summary: str = "",
    ) -> AgentProfile:
        inst_instruction = (
            f"\nAGENT TYPE: INSTITUTIONAL REPRESENTATIVE\nYou represent: {demographic_seed}\nEntity Context: {inst_summary}\n"
            "Your name, background, and occupation must reflect a formal representative or official of this institution."
            if is_institution else f"Demographic archetype to embody: {demographic_seed}"
        )
        
        user_msg = (
            f"Topic: {topic}\n"
            + (f"Context: {context[:600]}\n" if context else "")
            + f"Assigned opinion: {opinion.value.replace('_', ' ')}\n"
            f"Assigned social role: {role.value.replace('_', ' ')}\n"
            + inst_instruction +
            f"\nGenerate agent #{index + 1}. Ensure the name, background, and occupation are entirely unique."
        )
        try:
            data = await self._llm.complete_json(
                messages=[
                    {"role": "system", "content": _PERSONA_SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.9,
                max_tokens=400,
            )
        except Exception as exc:
            logger.warning("Agent %d generation failed (%s) — using fallback", index, exc)
            data = _fallback_persona(index)

        return AgentProfile(
            agent_id=str(uuid.uuid4()),
            name=str(data.get("name", f"Agent_{index}")),
            age=int(data.get("age", 30)),
            occupation=str(data.get("occupation", "professional")),
            background=str(data.get("background", "")),
            opinion_bias=opinion,
            influence_role=role,
            communication_style=str(data.get("communication_style", "casual")),
            expertise_domains=list(data.get("expertise_domains", [])),
            trusted_sources=list(data.get("trusted_sources", [])),
            reaction_speed=float(data.get("reaction_speed", 0.5)),
            susceptibility=float(data.get("susceptibility", 0.5)),
        )

    @staticmethod
    def _count_distribution(assignments: list[tuple[OpinionBias, InfluenceRole]]) -> list[int]:
        counts = [0] * 5
        for opinion, _ in assignments:
            counts[_OPINION_ORDER.index(opinion)] += 1
        return counts


def _quota_round(total: int, weights: list[float]) -> list[int]:
    """Largest-remainder rounding. Guarantees sum == total exactly."""
    exact     = [w * total for w in weights]
    floored   = [math.floor(x) for x in exact]
    remainder = [(exact[i] - floored[i], i) for i in range(len(exact))]
    deficit   = total - sum(floored)
    remainder.sort(reverse=True)
    for i in range(deficit):
        floored[remainder[i][1]] += 1
    return floored


def _fallback_persona(index: int) -> dict:
    """Minimal valid persona used when the LLM call fails."""
    return {
        "name":               f"Participant {index + 1}",
        "age":                30 + (index % 40),
        "occupation":         "community member",
        "background":         "A person with views on current events.",
        "communication_style":"casual",
        "expertise_domains":  ["general knowledge"],
        "trusted_sources":    ["news media"],
        "reaction_speed":     0.5,
        "susceptibility":     0.5,
    }