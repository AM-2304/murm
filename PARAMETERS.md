# MURM COMPLETE PARAMETER REFERENCE
# Every tunable value in the system, where it lives, what it does,
# and what changing it affects.

# TIER 1: .env FILE: Global defaults, no code change needed

DEFAULT_AGENTS=50
# File: config.py -> Settings.default_agents
# What: Pre-fills the agent count in the UI and CLI default.
# Effect: More agents = more diverse opinions, more LLM calls, higher cost.
#         Recommendation: Use 20 for testing, 50-100 for real runs.
#         Rule of thumb: double agents = double cost, diminishing returns above 100.

DEFAULT_ROUNDS=30
# File: config.py -> Settings.default_rounds
# What: Pre-fills the rounds slider in the UI.
# Effect: More rounds = more interaction cycles, slower convergence detection.
#         Recommendation: Use 15 for testing, 30-50 for real runs.

DEFAULT_SEED=42
# File: config.py -> Settings.default_seed
# What: The starting number for all randomness in the simulation.
# Effect: Same seed + same inputs = identical output every time.
#         Change this to get a different-but-reproducible run.

TOKEN_BUDGET=0
# File: config.py -> Settings.token_budget
# What: Hard cap on total tokens across the entire process.
# Effect: 0 = no limit. Any positive integer stops the run if exceeded.
#         200000 tokens ≈ $0.02 on Groq, $0.06 on gpt-4o-mini.

LOG_LEVEL=INFO
# File: config.py -> Settings.log_level
# What: How much detail appears in your terminal.
# Values: DEBUG (every LLM call), INFO (normal), WARNING (errors only)
# Recommendation: Use DEBUG when something is not working.

# TIER 2: API REQUEST BODY: Per-run overrides

# These are the values you set in the UI or pass in the API request body.
# They override the .env defaults for a single run only.

# n_agents: 5-500
#   UI: "Agents" slider in RunForm
#   API: {"n_agents": 30}
#   CLI: --agents 30

# n_rounds: 5-200
#   UI: "Rounds" slider in RunForm
#   API: {"n_rounds": 20}
#   CLI: --rounds 20

# seed: any integer
#   UI: "Random seed" field
#   API: {"seed": 99}
#   CLI: --seed 99

# n_sensitivity_seeds: 1-5
#   UI: "Sensitivity seeds" field
#   API: {"n_sensitivity_seeds": 3}
#   CLI: --seeds 3
#   Effect: Runs the simulation N times with seed, seed+1, seed+2...
#           and produces an uncertainty statement comparing outcomes.

# environment_type: "forum" or "town_hall"
#   UI: "Environment" dropdown
#   API: {"environment_type": "town_hall"}
#   CLI: --env town_hall
#   Effect: forum = open discussion noticeboard
#           town_hall = structured agenda, each round is an agenda item

# opinion_distribution: "normal", "bimodal", "power_law", "uniform"
#   UI: "Opinion distribution" dropdown
#   API: {"opinion_distribution": "bimodal"}
#   CLI: --opinion-dist bimodal
#   Effect: Controls starting stance spread across the population.

# skip_graph: true or false
#   UI: not in UI yet (API and CLI only)
#   API: {"skip_graph": true}
#   CLI: --skip-graph
#   Effect: Bypasses knowledge graph extraction. Faster but agents
#           have no factual grounding — more hallucination risk.

# multi-document ingestion: pass --seed-file multiple times
#   UI: Multiple file uploads per project
#   API: Supports multiple seed files + inline text
#   CLI: --seed-file doc1.pdf --seed-file doc2.txt ...
#   Effect: Fuses entities and discovers cross-document relations.

# counterfactual_events: list of {round, content, source}
#   UI: "Counterfactual events" builder in RunForm
#   API: {"counterfactual_events": [{"round": 10, "content": "New study contradicts claims", "source": "Reuters"}]}
#   CLI: not available (use API directly for this)

# TIER 3: CODE CONSTANTS: Structural changes, edit the source

# Agent influence role distribution
# File: murm/agents/generator.py, line ~35
# Variable: _INFLUENCE_ROLE_WEIGHTS
# Current values:
#   INFLUENCER: 5%     (high reach, infrequent posting)
#   ACTIVE_USER: 25%   (moderate reach and frequency)
#   PASSIVE_USER: 55%  (low reach, mostly reactive)
#   SKEPTIC: 10%       (challenges dominant narratives)
#   AMPLIFIER: 5%      (reposts/shares, low original content)
# Change to: reflect your domain's actual participation pattern.
# Example for a scientific community:
#   _INFLUENCE_ROLE_WEIGHTS = {
#       InfluenceRole.INFLUENCER: 0.03,
#       InfluenceRole.ACTIVE_USER: 0.40,
#       InfluenceRole.PASSIVE_USER: 0.35,
#       InfluenceRole.SKEPTIC: 0.15,
#       InfluenceRole.AMPLIFIER: 0.07,
#   }

# Opinion scale definitions
# File: murm/agents/model.py
# Enum: OpinionBias
# Current: strongly_agree, agree, neutral, disagree, strongly_disagree
# To add a domain-specific scale (e.g. for financial sentiment):
#   class OpinionBias(str, Enum):
#       BULLISH = "bullish"
#       CAUTIOUSLY_BULLISH = "cautiously_bullish"
#       NEUTRAL = "neutral"
#       CAUTIOUSLY_BEARISH = "cautiously_bearish"
#       BEARISH = "bearish"
# Then update _OPINION_VALUES in metrics.py accordingly.

# Environment context feed size
# File: murm/simulation/environment.py
# Method: get_context_feed(self, round_num, max_items=10)
# Default: 10 posts visible to each agent per round
# Effect: More = richer context but longer prompts and higher cost.
#         Less = faster and cheaper but agents have less to react to.
# To change globally:
#   def get_context_feed(self, round_num: int, max_items: int = 5) -> list[str]:

# RAG context per agent turn
# File: murm/simulation/engine.py, inside _agent_turn method
# Variable: top_k in embedder.query call (currently 3)
# Effect: How many knowledge graph facts each agent sees per turn.
#         Increase to reduce hallucination, at the cost of longer prompts.
# Current:
#   hits = self._embedder.query(state.last_action_summary, top_k=3)
# Change to top_k=5 for better grounding, top_k=1 for minimal cost.

# Distance threshold for RAG facts
# File: murm/simulation/engine.py, inside _agent_turn method
# Current: h["distance"] < 0.8 (filters out loosely related facts)
# Lower value = stricter matching (only very relevant facts shown)
# Higher value = looser matching (more facts shown, some less relevant)
# Change: h["distance"] < 0.6 for strict, h["distance"] < 0.9 for loose

# ReACT report agent iteration limit
# File: murm/analysis/report_agent.py
# Variable: MAX_REACT_ITERATIONS = 12
# Effect: Maximum number of tool calls before the report is written.
#         Increase for more thorough analysis (more cost).
#         Decrease for faster, cheaper but shallower reports.

# Sensitivity variance thresholds
# File: murm/analysis/calibration.py
# Function: _variance_label(std: float) -> str
# Current: low < 0.05, medium 0.05-0.15, high > 0.15
# Adjust to match your domain's expected variance.

# Entropy convergence detection
# File: murm/simulation/metrics.py
# Variable: _ENTROPY_CONVERGENCE_THRESHOLD = 0.05
# Effect: How stable opinion entropy must be (for 3 consecutive rounds)
#         before the system declares the simulation has "settled."

# Maximum concurrent agents per round
# File: murm/simulation/engine.py
# Class: SimulationConfig
# Field: max_concurrent_agents: int = 10
# Effect: How many agent LLM calls run in parallel.
#         Higher = faster simulation but more API rate limit risk.
#         Lower = safer but slower.
# Change in the API request body: {"max_concurrent_agents": 5}
# Or modify the dataclass default directly.

# TIER 4: PERSONA PROMPT: Change what kind of person is generated

# File: murm/agents/generator.py
# Variable: _PERSONA_SYSTEM (the system prompt for persona generation)
# Current: generates socially diverse archetypes via randomly seeded demographics
#          (e.g., "Gen Z College Student", "Rural Small Business Owner")
# To create domain-specific personas, change the system prompt.
#
# Example for financial analysts:
#   _PERSONA_SYSTEM = """You are creating realistic financial market participants.
#   Generate exactly ONE person profile as valid JSON.
#   The person must have genuine financial market experience.
#   Their opinion reflects their portfolio position and risk tolerance.
#   ... """
#
# Example for policy stakeholders:
#   _PERSONA_SYSTEM = """You are creating realistic policy stakeholders.
#   Each person represents a real constituency: NGO worker, small business owner,
#   academic researcher, government official, affected community member, etc.
#   ... """

# TIER 5: AGENT ACTION PROMPT: What agents actually DO each round

# File: murm/simulation/engine.py
# Variable: _AGENT_SYSTEM (the system prompt governing agent behavior)
# Current: Simulates social media users (post, reply, share, abstain)
#
# To simulate policy deliberation (not social media):
#   _AGENT_SYSTEM = """You are simulating a stakeholder in a policy consultation.
#   Stay completely in character. Respond ONLY with valid JSON:
#   {
#     "action": "statement" | "question" | "objection" | "support" | "abstain",
#     "content": "your spoken contribution (empty string if abstaining)",
#     "opinion_shift": "strongly_agree|agree|neutral|disagree|strongly_disagree or null",
#     "reasoning": "1 sentence internal justification"
#   }
#   opinion_shift reflects your stance AFTER the discussion — null if unchanged."""
#
# To simulate financial market commentary:
#   _AGENT_SYSTEM = """You are simulating a financial market participant.
#   Respond ONLY with valid JSON:
#   {
#     "action": "buy_signal" | "sell_signal" | "hold" | "comment" | "abstain",
#     "content": "your public comment or analysis",
#     "opinion_shift": "bullish|cautiously_bullish|neutral|cautiously_bearish|bearish or null",
#     "reasoning": "1 sentence rationale"
#   }"""
