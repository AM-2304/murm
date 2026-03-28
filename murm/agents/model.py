"""
Agent data model.
Every simulated agent is an instance of AgentProfile - a frozen description
of its persona that is generated once and read-only during the simulation.
AgentState is the mutable counterpart, updated each round.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OpinionBias(str, Enum):
    """
    Initial stance toward the simulation topic.
    Assigned during diversity initialization - not random, distributed
    to mirror a target opinion spectrum (e.g., normal, bimodal, power-law).
    """
    STRONGLY_AGREE = "strongly_agree"
    AGREE = "agree"
    NEUTRAL = "neutral"
    DISAGREE = "disagree"
    STRONGLY_DISAGREE = "strongly_disagree"


class InfluenceRole(str, Enum):
    """
    Communication archetype - determines posting frequency and reach.
    """
    INFLUENCER = "influencer"       # High reach, infrequent posting
    ACTIVE_USER = "active_user"     # Moderate reach and frequency
    PASSIVE_USER = "passive_user"   # Low reach, reactive
    SKEPTIC = "skeptic"             # Challenges dominant narratives
    AMPLIFIER = "amplifier"         # Reposts/shares, low original content


@dataclass(frozen=True)
class AgentProfile:
    """
    Immutable persona generated before simulation starts.
    All fields are set at construction time and never mutated.
    """
    agent_id: str
    name: str
    age: int
    occupation: str
    location: str                   # city/region/country
    ethnicity: str                  # ethnic/cultural background
    background: str                 # 2–3 sentence life context
    opinion_bias: OpinionBias
    influence_role: InfluenceRole
    communication_style: str        # e.g. "formal", "sarcastic", "empathetic"
    expertise_domains: list[str]    # Topics this agent speaks about with authority
    trusted_sources: list[str]      # Information sources this agent deems credible
    reaction_speed: float           # 0.0–1.0: how quickly they respond to new content
    susceptibility: float           # 0.0–1.0: how easily they shift opinion

    def to_prompt_context(self) -> str:
        """
        Render as a compact persona block for injection into agent prompts.
        """
        return (
            f"You are {self.name}, {self.age} years old, {self.occupation} from {self.location}.\n"
            f"Ethnicity: {self.ethnicity}\n"
            f"Background: {self.background}\n"
            f"Communication style: {self.communication_style}\n"
            f"Expertise: {', '.join(self.expertise_domains)}\n"
            f"Trusted sources: {', '.join(self.trusted_sources)}\n"
            f"Current stance on the topic: {self.opinion_bias.value}\n"
            f"You are a {self.influence_role.value}."
        )

    def to_dict(self) -> dict:
        def _get_val(obj):
            return obj.value if hasattr(obj, 'value') else str(obj)
            
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "age": self.age,
            "occupation": self.occupation,
            "location": self.location,
            "ethnicity": self.ethnicity,
            "background": self.background,
            "opinion_bias": _get_val(self.opinion_bias),
            "influence_role": _get_val(self.influence_role),
            "communication_style": self.communication_style,
            "expertise_domains": self.expertise_domains,
            "trusted_sources": self.trusted_sources,
            "reaction_speed": self.reaction_speed,
            "susceptibility": self.susceptibility,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentProfile":
        return cls(
            agent_id=d["agent_id"],
            name=d["name"],
            age=d["age"],
            occupation=d["occupation"],
            location=d.get("location", "unknown"),
            ethnicity=d.get("ethnicity", "diverse"),
            background=d["background"],
            opinion_bias=OpinionBias(d["opinion_bias"]),
            influence_role=InfluenceRole(d["influence_role"]),
            communication_style=d["communication_style"],
            expertise_domains=d["expertise_domains"],
            trusted_sources=d["trusted_sources"],
            reaction_speed=float(d["reaction_speed"]),
            susceptibility=float(d["susceptibility"]),
        )


@dataclass
class AgentState:
    """
    Mutable agent state updated each simulation round.
    Stored in the SQLite trace database alongside each action record.
    """
    agent_id: str
    current_round: int = 0
    current_opinion: OpinionBias = OpinionBias.NEUTRAL
    opinion_history: list[str] = field(default_factory=list)
    posts_made: int = 0
    interactions_received: int = 0
    last_action_summary: str = ""
    custom: dict[str, Any] = field(default_factory=dict)

    def shift_opinion(self, new_opinion: OpinionBias) -> None:
        if new_opinion != self.current_opinion:
            self.opinion_history.append(
                f"round {self.current_round}: {self.current_opinion.value} -> {new_opinion.value}"
            )
            self.current_opinion = new_opinion
