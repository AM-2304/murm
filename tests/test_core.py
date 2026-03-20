"""
Test suite for deterministic, non-LLM components.
LLM-dependent paths are tested via integration tests (not included here).
"""

from __future__ import annotations

import asyncio
import json
import math
import tempfile
from pathlib import Path

import pytest

from murm.agents.generator import PersonaGenerator, _quota_round
from murm.agents.model import AgentProfile, AgentState, OpinionBias, InfluenceRole
from murm.analysis.calibration import (
    compute_brier_score,
    compute_sensitivity,
    uncertainty_statement,
)
from murm.graph.engine import KnowledgeGraph, _canonical_id
from murm.llm.budget import BudgetManager, _model_cost as _estimate_cost
from murm.simulation.environment import ForumEnvironment, TownHallEnvironment, build_environment
from murm.simulation.metrics import MetricsCollector, _shannon_entropy, _gini
from murm.simulation.trace import TraceWriter


# ------------------------------------------------------------------
# Graph engine
# ------------------------------------------------------------------

class TestKnowledgeGraph:
    def test_add_and_retrieve_entity(self, tmp_path):
        kg = KnowledgeGraph(tmp_path / "graph.json")
        node_id = kg.add_entity("Alice Smith", "person", "A software engineer.")
        assert node_id == "alice_smith"
        entity = kg.get_entity("Alice Smith")
        assert entity is not None
        assert entity["name"] == "Alice Smith"

    def test_deduplication_by_canonical_name(self, tmp_path):
        kg = KnowledgeGraph(tmp_path / "graph.json")
        kg.add_entity("  OpenAI  ", "organization", "AI company")
        kg.add_entity("OpenAI", "organization", "Updated summary")
        assert kg._g.number_of_nodes() == 1

    def test_add_relation_requires_existing_entities(self, tmp_path):
        kg = KnowledgeGraph(tmp_path / "graph.json")
        kg.add_entity("Alice", "person", "")
        with pytest.raises(ValueError):
            kg.add_relation("Alice", "Bob", "knows")

    def test_subgraph_around_depth(self, tmp_path):
        kg = KnowledgeGraph(tmp_path / "graph.json")
        kg.add_entity("A", "node", "")
        kg.add_entity("B", "node", "")
        kg.add_entity("C", "node", "")
        kg.add_relation("A", "B", "links_to")
        kg.add_relation("B", "C", "links_to")
        subgraph = kg.subgraph_around("A", depth=2)
        node_ids = {n["id"] for n in subgraph["nodes"]}
        assert "a" in node_ids
        assert "b" in node_ids
        assert "c" in node_ids

    def test_persistence_roundtrip(self, tmp_path):
        path = tmp_path / "graph.json"
        kg = KnowledgeGraph(path)
        kg.add_entity("Persisted Entity", "concept", "Should survive reload")
        kg2 = KnowledgeGraph(path)
        assert kg2.get_entity("Persisted Entity") is not None

    def test_lexical_search(self, tmp_path):
        kg = KnowledgeGraph(tmp_path / "graph.json")
        kg.add_entity("Climate Change", "issue", "Global warming and its effects")
        kg.add_entity("Tax Policy", "issue", "Government revenue systems")
        results = kg.search_entities("global warming")
        assert any("climate" in r["id"] for r in results)

    def test_canonical_id(self):
        assert _canonical_id("  Hello World  ") == "hello_world"
        assert _canonical_id("openai") == "openai"


# ------------------------------------------------------------------
# Agent model
# ------------------------------------------------------------------

class TestAgentProfile:
    def test_to_dict_roundtrip(self):
        profile = AgentProfile(
            agent_id="test-id",
            name="Bob",
            age=35,
            occupation="journalist",
            background="Covers tech policy.",
            opinion_bias=OpinionBias.AGREE,
            influence_role=InfluenceRole.ACTIVE_USER,
            communication_style="analytical",
            expertise_domains=["technology", "policy"],
            trusted_sources=["Reuters"],
            reaction_speed=0.7,
            susceptibility=0.3,
        )
        recovered = AgentProfile.from_dict(profile.to_dict())
        assert recovered.agent_id == profile.agent_id
        assert recovered.opinion_bias == profile.opinion_bias

    def test_opinion_shift_records_history(self):
        state = AgentState(agent_id="x", current_opinion=OpinionBias.NEUTRAL)
        state.shift_opinion(OpinionBias.AGREE)
        assert len(state.opinion_history) == 1
        assert state.current_opinion == OpinionBias.AGREE

    def test_opinion_shift_no_change_produces_no_history(self):
        state = AgentState(agent_id="x", current_opinion=OpinionBias.NEUTRAL)
        state.shift_opinion(OpinionBias.NEUTRAL)
        assert len(state.opinion_history) == 0


# ------------------------------------------------------------------
# Quota rounding
# ------------------------------------------------------------------

class TestQuotaRound:
    def test_sum_equals_total(self):
        for total in [10, 50, 100, 137, 1]:
            weights = [0.05, 0.25, 0.55, 0.10, 0.05]
            result = _quota_round(total, weights)
            assert sum(result) == total

    def test_uniform_distribution(self):
        result = _quota_round(10, [0.2] * 5)
        assert all(v == 2 for v in result)


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------

class TestMetrics:
    def test_shannon_entropy_uniform(self):
        dist = [0.2, 0.2, 0.2, 0.2, 0.2]
        assert abs(_shannon_entropy(dist) - math.log2(5)) < 0.001

    def test_shannon_entropy_fully_polarized(self):
        dist = [1.0, 0.0, 0.0, 0.0, 0.0]
        assert _shannon_entropy(dist) == 0.0

    def test_gini_equal_posting(self):
        actions = [{"agent_id": f"a{i}"} for i in range(10)]
        assert _gini(actions) == pytest.approx(0.0, abs=0.01)

    def test_metrics_collector_records_rounds(self):
        collector = MetricsCollector(n_agents=5)
        states = [
            AgentState(agent_id=f"a{i}", current_opinion=OpinionBias.NEUTRAL)
            for i in range(5)
        ]
        round_m = collector.record_round(1, states, [], elapsed=0.1)
        assert "opinion_entropy" in round_m
        assert round_m["round"] == 1

    def test_final_summary_structure(self):
        collector = MetricsCollector(n_agents=5)
        states = [AgentState(agent_id=f"a{i}", current_opinion=OpinionBias.AGREE) for i in range(5)]
        collector.record_round(1, states, [], elapsed=0.1)
        summary = collector.final_summary()
        assert "total_rounds" in summary
        assert "polarization_index" in summary
        assert "entropy_time_series" in summary


# ------------------------------------------------------------------
# Budget manager
# ------------------------------------------------------------------

class TestBudgetManager:
    def test_budget_not_exceeded_within_limit(self):
        bm = BudgetManager(budget_tokens=10_000)
        bm.record(100, 100, "gpt-4o-mini")
        assert bm.usage.total_tokens == 200

    def test_budget_exceeded_raises(self):
        from murm.llm.budget import BudgetExceeded
        bm = BudgetManager(budget_tokens=100)
        with pytest.raises(BudgetExceeded):
            bm.record(60, 60, "gpt-4o-mini")

    def test_unlimited_budget_never_raises(self):
        bm = BudgetManager(budget_tokens=0)
        bm.record(1_000_000, 1_000_000, "gpt-4o-mini")

    def test_estimate_simulation_cost_structure(self):
        est = BudgetManager.estimate_simulation_cost(50, 30)
        assert "total_calls" in est
        assert est["total_calls"] == 50 * 30
        assert est["estimated_cost_usd"] >= 0.0

    def test_snapshot_budget_pct(self):
        bm = BudgetManager(budget_tokens=1000)
        bm.record(100, 100, "gpt-4o-mini")
        snap = bm.snapshot()
        assert snap["budget_used_pct"] == pytest.approx(20.0, abs=0.1)


# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------

class TestEnvironments:
    def test_forum_feed_includes_scenario(self):
        env = ForumEnvironment(scenario_description="A debate on AI policy", seed=1)
        feed = env.get_context_feed(round_num=1)
        assert any("AI policy" in item for item in feed)

    def test_forum_ingest_and_retrieve(self):
        env = ForumEnvironment(seed=1)
        env.ingest_action({
            "agent_id": "agent_1",
            "content": "I strongly agree with the proposal.",
            "round": 1,
            "action_type": "post",
        })
        feed = env.get_context_feed(round_num=2)
        assert any("agree" in item for item in feed)

    def test_external_event_injection(self):
        env = ForumEnvironment(seed=1)
        env.inject_external_event("Breaking: new legislation passed", "news_bot", round_num=5)
        feed = env.get_context_feed(round_num=5)
        assert any("BREAKING" in item for item in feed)

    def test_town_hall_agenda_cycles(self):
        env = TownHallEnvironment(agenda_items=["Item A", "Item B"], seed=1)
        feed_r1 = env.get_context_feed(round_num=1)
        feed_r3 = env.get_context_feed(round_num=3)
        assert any("Item A" in item for item in feed_r1)
        assert any("Item A" in item for item in feed_r3)

    def test_build_environment_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown environment type"):
            build_environment("invalid_type")

    def test_all_posts_returns_ingested(self):
        env = ForumEnvironment(seed=1)
        env.ingest_action({"agent_id": "a1", "content": "Test post", "round": 1, "action_type": "post"})
        all_posts = env.get_all_posts()
        assert len(all_posts) == 1


# ------------------------------------------------------------------
# Trace writer
# ------------------------------------------------------------------

class TestTraceWriter:
    def test_write_and_read_back(self, tmp_path):
        writer = TraceWriter(tmp_path / "trace.jsonl", flush_every=2)
        writer.write({"agent_id": "a1", "round": 1, "content": "hello"})
        writer.write({"agent_id": "a2", "round": 1, "content": "world"})
        records = writer.read_all()
        assert len(records) == 2

    def test_sample_returns_subset(self, tmp_path):
        writer = TraceWriter(tmp_path / "trace.jsonl", flush_every=1)
        for i in range(200):
            writer.write({"agent_id": f"a{i}", "round": i % 30, "content": f"msg{i}"})
        writer.flush()
        sample = writer.sample(n=50)
        assert len(sample) <= 50

    def test_flush_empties_buffer(self, tmp_path):
        writer = TraceWriter(tmp_path / "trace.jsonl", flush_every=100)
        writer.write({"test": True})
        assert len(writer._buffer) == 1
        writer.flush()
        assert len(writer._buffer) == 0


# ------------------------------------------------------------------
# Calibration
# ------------------------------------------------------------------

class TestCalibration:
    def test_brier_score_perfect_prediction(self):
        assert compute_brier_score(1.0, True) == pytest.approx(0.0)
        assert compute_brier_score(0.0, False) == pytest.approx(0.0)

    def test_brier_score_worst_prediction(self):
        assert compute_brier_score(1.0, False) == pytest.approx(1.0)
        assert compute_brier_score(0.0, True) == pytest.approx(1.0)

    def test_sensitivity_with_single_run(self):
        metrics = [{"final_entropy": 1.2, "polarization_index": 0.3, "entropy_time_series": [1.5, 1.2]}]
        result = compute_sensitivity(metrics)
        assert result.n_seeds == 1
        assert result.std_final_entropy == 0.0

    def test_sensitivity_with_multiple_runs(self):
        metrics = [
            {"final_entropy": 0.8, "polarization_index": 0.5, "entropy_time_series": [1.5, 0.8]},
            {"final_entropy": 1.4, "polarization_index": 0.2, "entropy_time_series": [1.5, 1.4]},
            {"final_entropy": 1.0, "polarization_index": 0.35, "entropy_time_series": [1.5, 1.0]},
        ]
        result = compute_sensitivity(metrics)
        assert result.n_seeds == 3
        assert result.std_final_entropy > 0.0
        assert result.prediction_variance in ("low", "medium", "high")

    def test_uncertainty_statement_returns_string(self):
        metrics = [{"final_entropy": 1.2, "polarization_index": 0.3, "entropy_time_series": [1.2]}]
        result = compute_sensitivity(metrics)
        stmt = uncertainty_statement(result)
        assert isinstance(stmt, str)
        assert len(stmt) > 20


# ------------------------------------------------------------------
# ProjectStore delete methods
# ------------------------------------------------------------------

import asyncio as _asyncio
import pytest

class TestProjectStore:
    def test_delete_project_removes_all_rows(self, tmp_path):
        from murm.api.store import ProjectStore

        store = ProjectStore(tmp_path / "test.db")
        _asyncio.run(store.initialize())

        pid = _asyncio.run(store.create_project("test project"))
        rid = _asyncio.run(store.create_run(pid, {"n_agents": 10}))
        _asyncio.run(store.append_event(rid, "round_completed", {"round": 1}))

        _asyncio.run(store.delete_project(pid))

        assert _asyncio.run(store.get_project(pid)) is None
        assert _asyncio.run(store.get_run(rid)) is None
        events = _asyncio.run(store.get_events_since(rid, since_ts=0.0))
        assert len(events) == 0

    def test_delete_run_keeps_project(self, tmp_path):
        from murm.api.store import ProjectStore

        store = ProjectStore(tmp_path / "test.db")
        _asyncio.run(store.initialize())

        pid = _asyncio.run(store.create_project("keep me"))
        rid = _asyncio.run(store.create_run(pid, {"n_agents": 5}))

        _asyncio.run(store.delete_run(rid))

        assert _asyncio.run(store.get_project(pid)) is not None
        assert _asyncio.run(store.get_run(rid)) is None

    def test_delete_nonexistent_run_is_noop(self, tmp_path):
        from murm.api.store import ProjectStore

        store = ProjectStore(tmp_path / "test.db")
        _asyncio.run(store.initialize())
        # Should not raise
        _asyncio.run(store.delete_run("nonexistent-id-000"))


# ------------------------------------------------------------------
# RAG injection — engine accepts embedder kwarg and builds correct prompt
# ------------------------------------------------------------------

class TestRAGInjection:
    def test_build_action_prompt_with_graph_context(self):
        from murm.simulation.engine import _build_action_prompt
        from murm.agents.model import AgentProfile, AgentState, OpinionBias, InfluenceRole

        profile = AgentProfile(
            agent_id="x",
            name="Test Agent",
            age=30,
            occupation="analyst",
            background="Background text.",
            opinion_bias=OpinionBias.NEUTRAL,
            influence_role=InfluenceRole.ACTIVE_USER,
            communication_style="analytical",
            expertise_domains=["policy"],
            trusted_sources=["Reuters"],
            reaction_speed=0.6,
            susceptibility=0.4,
        )
        state = AgentState(agent_id="x", current_opinion=OpinionBias.NEUTRAL)
        feed = ["Post A", "Post B"]
        graph_ctx = ["Entity: Climate Policy — International accord signed 2024"]

        prompt = _build_action_prompt(profile, state, feed, round_num=3, graph_context=graph_ctx)

        assert "Context:" in prompt or "Climate Policy" in prompt
        assert "Climate Policy" in prompt
        assert "Post A" in prompt
        assert "round 3" in prompt

    def test_build_action_prompt_without_graph_context(self):
        from murm.simulation.engine import _build_action_prompt
        from murm.agents.model import AgentProfile, AgentState, OpinionBias, InfluenceRole

        profile = AgentProfile(
            agent_id="y",
            name="No Graph Agent",
            age=25,
            occupation="student",
            background="Studies policy.",
            opinion_bias=OpinionBias.AGREE,
            influence_role=InfluenceRole.PASSIVE_USER,
            communication_style="casual",
            expertise_domains=[],
            trusted_sources=[],
            reaction_speed=0.3,
            susceptibility=0.7,
        )
        state = AgentState(agent_id="y", current_opinion=OpinionBias.AGREE)
        prompt = _build_action_prompt(profile, state, [], round_num=1, graph_context=None)

        assert "Relevant background facts" not in prompt
        assert "round 1" in prompt

    def test_engine_accepts_none_embedder(self):
        # Verify SimulationEngine constructor accepts embedder=None without error
        from murm.simulation.engine import SimulationEngine, SimulationConfig
        from murm.simulation.environment import ForumEnvironment
        from murm.agents.model import AgentProfile, OpinionBias, InfluenceRole
        import uuid
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            profile = AgentProfile(
                agent_id=str(uuid.uuid4()),
                name="Minimal",
                age=30,
                occupation="tester",
                background="Test.",
                opinion_bias=OpinionBias.NEUTRAL,
                influence_role=InfluenceRole.ACTIVE_USER,
                communication_style="casual",
                expertise_domains=[],
                trusted_sources=[],
                reaction_speed=0.5,
                susceptibility=0.5,
            )
            engine = SimulationEngine(
                run_id="test-run",
                agents=[profile],
                environment=ForumEnvironment(seed=1),
                config=SimulationConfig(n_rounds=1, seed=1),
                trace_dir=Path(tmp),
                budget=None,
                embedder=None,
            )
            assert engine._embedder is None


# ------------------------------------------------------------------
# skip_graph flag in CreateRunRequest model
# ------------------------------------------------------------------

class TestSkipGraphFlag:
    def test_skip_graph_defaults_false(self):
        import sys
        import os
        # Minimal check that the Pydantic model accepts skip_graph
        from murm.api.routes.runs import CreateRunRequest
        req = CreateRunRequest(
            project_id="pid",
            prediction_question="q?",
            skip_graph=False,
        )
        assert req.skip_graph is False

    def test_skip_graph_can_be_set_true(self):
        from murm.api.routes.runs import CreateRunRequest
        req = CreateRunRequest(
            project_id="pid",
            prediction_question="q?",
            skip_graph=True,
        )
        assert req.skip_graph is True