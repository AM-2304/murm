"""
Pluggable environment abstraction.

MiroFish hard-codes Twitter and Reddit as two parallel subprocess simulations.
Here, Environment is an abstract base class. Built-in implementations:
  - ForumEnvironment: threaded discussion board (neutral domain)
  - TownHallEnvironment: structured public deliberation (policy scenarios)

Custom environments extend Environment and pass them to SimulationEngine.
The engine calls three methods only: get_context_feed(), ingest_action(), inject_external_event().
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class EnvironmentPost:
    author_id: str
    content: str
    round_num: int
    action_type: str = "post"
    parent_id: str | None = None


class Environment(ABC):
    """
    Abstract interface every environment must implement.
    Environments maintain an internal message feed that agents read each round.
    """

    @abstractmethod
    def get_context_feed(self, round_num: int, max_items: int = 10) -> list[str]:
        """
        Return up to max_items recent messages relevant to this round.
        Called before each agent's turn.
        """

    @abstractmethod
    def ingest_action(self, action: dict) -> None:
        """
        Add an agent's action to the environment feed.
        Called after each successful agent turn.
        """

    @abstractmethod
    def inject_external_event(self, content: str, source: str, round_num: int) -> None:
        """
        Inject an externally authored event (counterfactual injection).
        This content will appear in the feed for all subsequent agents.
        """

    @abstractmethod
    def get_all_posts(self) -> list[dict]:
        """Return all posts for the trace and report agent."""


class ForumEnvironment(Environment):
    """
    Threaded discussion forum.
    Recent posts visible to all agents, replies visible in thread context.
    Context feed shows the N most recent posts plus any pinned events.
    """

    def __init__(self, scenario_description: str = "", seed: int = 42) -> None:
        self._scenario = scenario_description
        self._posts: list[EnvironmentPost] = []
        self._pinned: list[str] = []  # injected events always visible
        self._rng = random.Random(seed)
        # Seed the feed with the scenario description so round-1 agents have context
        if scenario_description:
            self._pinned.append(f"[Scenario] {scenario_description}")

    def get_context_feed(self, round_num: int, max_items: int = 10) -> list[str]:
        recent = [
            f"[@{p.author_id[:8]}] {p.content}"
            for p in self._posts[-(max_items - len(self._pinned)):]
        ]
        return self._pinned + recent

    def ingest_action(self, action: dict) -> None:
        if not action.get("content"):
            return
        self._posts.append(EnvironmentPost(
            author_id=action["agent_id"],
            content=action["content"],
            round_num=action["round"],
            action_type=action.get("action_type", "post"),
        ))

    def inject_external_event(self, content: str, source: str, round_num: int) -> None:
        pinned_msg = f"[BREAKING - {source}] {content}"
        self._pinned.append(pinned_msg)
        self._posts.append(EnvironmentPost(
            author_id=source,
            content=content,
            round_num=round_num,
            action_type="external_event",
        ))

    def get_all_posts(self) -> list[dict]:
        return [
            {
                "author_id": p.author_id,
                "content": p.content,
                "round": p.round_num,
                "type": p.action_type,
            }
            for p in self._posts
        ]


class TownHallEnvironment(Environment):
    """
    Structured public deliberation - agents take turns speaking on an agenda.
    Each round corresponds to one agenda item.
    Useful for policy scenarios, governance simulations, public consultations.
    """

    def __init__(
        self,
        agenda_items: list[str] | None = None,
        scenario_description: str = "",
        seed: int = 42,
    ) -> None:
        self._agenda = agenda_items or []
        self._scenario = scenario_description
        self._posts: list[EnvironmentPost] = []
        self._external_events: list[str] = []
        self._rng = random.Random(seed)

    def get_context_feed(self, round_num: int, max_items: int = 10) -> list[str]:
        agenda_item = (
            self._agenda[(round_num - 1) % len(self._agenda)]
            if self._agenda
            else "Open discussion"
        )
        feed = [f"[AGENDA ITEM {round_num}] {agenda_item}"]
        feed += self._external_events[-3:]
        recent_posts = self._posts[-(max_items - len(feed)):]
        feed += [f"[@{p.author_id[:8]}] {p.content}" for p in recent_posts]
        return feed

    def ingest_action(self, action: dict) -> None:
        if not action.get("content"):
            return
        self._posts.append(EnvironmentPost(
            author_id=action["agent_id"],
            content=action["content"],
            round_num=action["round"],
            action_type=action.get("action_type", "post"),
        ))

    def inject_external_event(self, content: str, source: str, round_num: int) -> None:
        self._external_events.append(f"[{source}] {content}")
        self._posts.append(EnvironmentPost(
            author_id=source,
            content=content,
            round_num=round_num,
            action_type="external_event",
        ))

    def get_all_posts(self) -> list[dict]:
        return [
            {
                "author_id": p.author_id,
                "content": p.content,
                "round": p.round_num,
                "type": p.action_type,
            }
            for p in self._posts
        ]


class NetworkedEnvironment(Environment):
    """
    Simulates a social media algorithmic feed with echo chambers and follower networks.
    Instead of a pure chronological feed, feeds are personalized per agent.
    """

    def __init__(self, scenario_description: str = "", seed: int = 42) -> None:
        self._scenario = scenario_description
        self._seed = seed
        self._posts: list[EnvironmentPost] = []
        self._pinned: list[str] = []
        self._rng = random.Random(seed)
        if scenario_description:
            self._pinned.append(f"[Scenario] {scenario_description}")

    def get_context_feed(self, round_num: int, max_items: int = 10, agent_id: str | None = None) -> list[str]:
        # Algorithmic feed logic: 
        # 1. Always show pinned/breaking news
        # 2. Show recent posts, but probabilistically filtered to simulate algorithmic visibility
        feed = self._pinned.copy()
        remaining_slots = max_items - len(feed)
        
        if remaining_slots > 0 and self._posts:
            # Sort by recentness
            recent = self._posts[-50:]
            # The "algorithm" picks a personalized subset. We use a seeded random based on agent_id
            # so the feed is stable within the round but unique to the agent's simulated network.
            algo_rng = random.Random(f"{agent_id}_{round_num}_{self._seed}")
            
            selected = algo_rng.sample(recent, min(len(recent), remaining_slots))
            # Sort chronologically for readibility
            selected.sort(key=lambda p: p.round_num)
            
            feed += [f"[@{p.author_id[:8]}] {p.content}" for p in selected]
            
        return feed

    def ingest_action(self, action: dict) -> None:
        if not action.get("content"):
            return
        self._posts.append(EnvironmentPost(
            author_id=action["agent_id"],
            content=action["content"],
            round_num=action["round"],
            action_type=action.get("action_type", "post"),
        ))

    def inject_external_event(self, content: str, source: str, round_num: int) -> None:
        pinned_msg = f"[VIRAL ALGORITHM BOOST — {source}] {content}"
        self._pinned.append(pinned_msg)
        self._posts.append(EnvironmentPost(
            author_id=source,
            content=content,
            round_num=round_num,
            action_type="external_event",
        ))

    def get_all_posts(self) -> list[dict]:
        return [
            {
                "author_id": p.author_id,
                "content": p.content,
                "round": p.round_num,
                "type": p.action_type,
            }
            for p in self._posts
        ]


def build_environment(
    env_type: str,
    scenario_description: str = "",
    seed: int = 42,
    **kwargs,
) -> Environment:
    """
    Factory that constructs an environment by type string.
    Extend the registry dict to add custom environments.
    """
    registry: dict[str, type[Environment]] = {
        "forum": ForumEnvironment,
        "town_hall": TownHallEnvironment,
        "network": NetworkedEnvironment,
    }
    cls = registry.get(env_type.lower())
    if cls is None:
        raise ValueError(
            f"Unknown environment type '{env_type}'. "
            f"Available: {list(registry.keys())}"
        )
    return cls(scenario_description=scenario_description, seed=seed, **kwargs)
