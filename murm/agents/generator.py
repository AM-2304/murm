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
import itertools
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

# Explicitly cycling through 16 world regions forces the LLM to produce
# genuinely diverse populations instead of repeating one ethnicity.
_GLOBAL_REGIONS = [
    "Nigeria (West Africa)",
    "Japan (East Asia)",
    "Brazil (South America)",
    "Germany (Western Europe)",
    "India (South Asia)",
    "Mexico (Central America)",
    "South Korea (East Asia)",
    "Kenya (East Africa)",
    "United States (North America)",
    "Turkey (Middle East/Europe)",
    "Australia (Oceania)",
    "Poland (Eastern Europe)",
    "Egypt (North Africa)",
    "Argentina (South America)",
    "Philippines (Southeast Asia)",
    "Canada (North America)",
]

# Note: no JSON fences instruction needed here — complete_json() appends it automatically
_PERSONA_SYSTEM = """You are a social scientist creating realistic simulation personas.
Generate exactly ONE person profile. The person must fit the assigned opinion and role.
The person MUST belong to the ASSIGNED GEOGRAPHY. Use a culturally authentic name, location, and background for that region.
Do NOT repeat names or demographics from previous agents.

Return ONLY a JSON object with these exact keys:
name (full name string — must be culturally authentic for the assigned geography),
age (integer 18-75), occupation (specific job title string),
location (city/region/country string), ethnicity (string),
background (2 sentence string of life context including cultural/geographic nuance),
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
        
        # Detect primary geography from context to ground demographics
        geography = await self._detect_geography(topic, context)
        
        logger.info(
            "Generating %d agents in %s, distribution=%s",
            n_agents, geography or "global/random", opinion_dist,
        )

        # Generate in concurrent batches of 5 - faster than sequential
        profiles: list[AgentProfile] = []
        tasks = []
        BATCH = 5
        
        # If institutions are provided, assign some agents to represent them
        institution_list = institutions or []
        n_inst = min(len(institution_list), max(1, n_agents // 10))
        
        # Brainstorm sector-specific archetypes for this topic
        archetypes = await self._brainstorm_archetypes(topic, context)
        
        for i, (opinion, role) in enumerate(assignments):
            # Determine if this agent should be an institutional representative
            is_institution_agent = i < n_inst
            inst_data = institution_list[i % len(institution_list)] if is_institution_agent else None
            
            tasks.append(
                self._generate_one(
                    i, topic, context, opinion, role,
                    demographic_seed=inst_data["name"] if inst_data else self._rng.choice(archetypes),
                    geography=geography,
                    is_institution=is_institution_agent,
                    inst_summary=inst_data.get("summary", "") if inst_data else ""
                )
            )
            
            if len(tasks) >= BATCH:
                batch_profiles = await asyncio.gather(*tasks, return_exceptions=False)
                profiles.extend(batch_profiles)
                tasks = []
                logger.info("Generated agents up to %d / %d", len(profiles), n_agents)

        if tasks:
            batch_profiles = await asyncio.gather(*tasks, return_exceptions=False)
            profiles.extend([p for p in batch_profiles if p is not None])

        return profiles[:n_agents]

    async def _detect_geography(self, topic: str, context: str) -> str | None:
        """Extracts the primary country/region mentioned in the context, if any."""
        if not context:
            return None
        prompt = (
            f"Given this topic and context, identify the primary country or region it pertains to.\n"
            f"Topic: {topic}\nContext: {context[:1000]}\n"
            "If a specific country or city is mentioned as the primary location, return only the name (e.g. 'United States' or 'New York'). "
            "If multiple or none, return 'None'."
        )
        try:
            res = await self._llm.complete([{"role": "user", "content": prompt}], max_tokens=20)
            clean = str(res).strip().strip("'\"")
            return None if clean == "None" or len(clean) > 30 else clean
        except Exception:
            return None

    async def _brainstorm_archetypes(self, topic: str, context: str) -> list[str]:
        """Dynamically generate sector-relevant archetypes to avoid industry bias."""
        prompt = (
            f"Brainstorm 8 diverse person archetypes (demographics and ideological roles) "
            f"that have a major stake in the following topic: {topic}\n"
            f"Context: {context[:500]}\n"
            "Return ONLY a bullet-point list of 8 archetypes, each 5-8 words long. "
            "Ensure they represent different age groups, socio-economic backgrounds, and expertise levels."
        )
        try:
            raw = await self._llm.complete([{"role": "user", "content": prompt}], max_tokens=300)
            lines = [line.strip("- ").strip("* ") for line in raw.split("\n") if len(line.strip()) > 10]
            return lines[:8] if len(lines) >= 4 else [
                "Young urban professional, tech-savvy", "Small business owner", "Retired educator", "Graduate student"
            ]
        except Exception:
            return ["Community member", "Professional", "Student", "Advocate"]

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
        geography: str | None = None,
        is_institution: bool = False,
        inst_summary: str = "",
    ) -> AgentProfile:
        if geography:
            geo_instruction = f"\nASSIGNED GEOGRAPHY: {geography}"
        else:
            # Rotate through global regions so every agent gets a different one
            region = _GLOBAL_REGIONS[index % len(_GLOBAL_REGIONS)]
            geo_instruction = f"\nASSIGNED GEOGRAPHY: {region}. The agent MUST be from this region with an authentic name and background."
        
        inst_instruction = (
            f"\nAGENT TYPE: INSTITUTIONAL REPRESENTATIVE\nYou represent: {demographic_seed}\nEntity Context: {inst_summary}\n"
            "Your name, background, and occupation must reflect a formal representative or official of this institution."
            if is_institution else f"Demographic archetype to embody: {demographic_seed}"
        )
        
        user_msg = (
            f"Topic: {topic}\n"
            + (f"Context: {str(context)[0:600]}\n" if context else "")
            + f"Assigned opinion: {opinion.value.replace('_', ' ')}\n"
            f"Assigned social role: {role.value.replace('_', ' ')}\n"
            + geo_instruction
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

        # Augment data with opinion and role for robust enum instantiation
        final_data = dict(data) if isinstance(data, dict) else {}
        final_data["opinion_bias"] = str(opinion.value)
        final_data["influence_role"] = str(role.value)

        return AgentProfile(
            agent_id=str(uuid.uuid4()),
            name=str(final_data.get("name", f"Agent_{index}")),
            age=int(final_data.get("age", 30)),
            occupation=str(final_data.get("occupation", "professional")),
            location=str(final_data.get("location", "unknown")),
            ethnicity=str(final_data.get("ethnicity", "diverse")),
            background=str(final_data.get("background", "")),
            opinion_bias=opinion,
            influence_role=role,
            communication_style=str(final_data.get("communication_style", "casual")),
            expertise_domains=list(final_data.get("expertise_domains", [])),
            trusted_sources=list(final_data.get("trusted_sources", [])),
            reaction_speed=float(final_data.get("reaction_speed", 0.5)),
            susceptibility=float(final_data.get("susceptibility", 0.5)),
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