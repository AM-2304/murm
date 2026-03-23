// Static Demo Data — matches the exact event shapes that
// useSimulation.js, AgentFeed.jsx, MetricsDashboard.jsx,
// ReportView.jsx, and AgentRoster.jsx all consume.


export const MOCK_GRAPH = {
  nodes: [
    { id: "Federal Reserve", type: "organization", summary: "The central bank of the US" },
    { id: "Interest Rates", type: "concept", summary: "Currently set at 5.25%-5.50%" },
    { id: "Core Inflation", type: "concept", summary: "Persistent economic indicator cited for holding rates" },
    { id: "Dot Plot", type: "artifact", summary: "Projections showing 3 rate cuts next year" },
    { id: "Public Sentiment", type: "concept", summary: "The public reaction to the Fed's competence" },
    { id: "Investors", type: "group", summary: "Market participants anticipating easing" },
    { id: "Consumers", type: "group", summary: "General public facing high living costs" }
  ],
  links: [
    { source: "Federal Reserve", target: "Interest Rates", label: "maintains" },
    { source: "Federal Reserve", target: "Core Inflation", label: "cites as reason" },
    { source: "Federal Reserve", target: "Dot Plot", label: "publishes" },
    { source: "Dot Plot", target: "Interest Rates", label: "projects cuts for" },
    { source: "Investors", target: "Dot Plot", label: "monitors closely" },
    { source: "Consumers", target: "Core Inflation", label: "impacted by" },
    { source: "Public Sentiment", target: "Federal Reserve", label: "evaluates competence of" }
  ]
};

export const MOCK_AGENT_PROFILES = [
  { agent_id: "agent_0", name: "Elena Vasquez", age: 34, occupation: "Retail Investor", opinion_bias: "disagree", backstory: "Lost savings during the 2022 rate hike cycle. Deeply skeptical of the Fed's ability to control inflation without hurting ordinary people." },
  { agent_id: "agent_1", name: "Marcus Chen", age: 52, occupation: "Macro-Economist, Federal Advisory Council", opinion_bias: "agree", backstory: "Published three papers on dual-mandate monetary policy. Believes the Fed's patience is the correct long-term strategy." },
  { agent_id: "agent_2", name: "Sarah Okonkwo", age: 41, occupation: "Small Business Owner (Bakery Chain)", opinion_bias: "strongly_disagree", backstory: "Took out SBA loans at variable rates in 2023. Current debt servicing is threatening her 3-location operation." },
  { agent_id: "agent_3", name: "David Park", age: 28, occupation: "Quantitative Day Trader", opinion_bias: "strongly_agree", backstory: "Manages a $2M personal portfolio heavily leveraged on rate-cut momentum trades. Lives and dies by the dot plot." },
  { agent_id: "agent_4", name: "Chloe Andersen", age: 45, occupation: "Senior Financial Journalist, Reuters", opinion_bias: "neutral", backstory: "Covered every FOMC meeting since 2015. Known for her ability to synthesize Wall Street and Main Street perspectives." }
];

// These are the SSE events in the EXACT format useSimulation.js expects.
// The hook listens for: agents_ready, round_completed, simulation_ended
export const MOCK_SSE_EVENTS = [
  // 1. Agent generation event
  {
    type: "agents_ready",
    payload: {
      profiles: MOCK_AGENT_PROFILES
    }
  },
  // 2. Round 1
  {
    type: "round_completed",
    payload: {
      round: 1,
      actions: 5,
      metrics: { opinion_entropy: 1.54, polarization_index: 0.62, gini_coefficient: 0.20, opinion_velocity: 0.40 },
      budget: { total_tokens: 4200, total_cost: 0.0008 },
      sample_actions: [
        { agent_id: "agent_1", round: 1, action_type: "post", content: "The Fed is doing exactly what it must. Core inflation hasn't yielded yet; holding rates at 5.25% is prudent. The dual mandate demands patience, not panic.", opinion_shift: "neutral" },
        { agent_id: "agent_0", round: 1, action_type: "reply", content: "Prudent for who? We are being squeezed by these rates and inflation isn't dropping for everyday goods. The Fed is catastrophically slow and disconnected from reality.", opinion_shift: "disagree" },
        { agent_id: "agent_3", round: 1, action_type: "post", content: "Ignore the hold — the real signal is the 3 cuts on the dot plot. The market is pricing in an aggressive easing cycle. Liquidity is coming, and it's going to be explosive.", opinion_shift: "strongly_agree" },
        { agent_id: "agent_2", round: 1, action_type: "post", content: "Can my business survive another year of this? 'Next year' is too far away when you have payroll loans at 8.5% TODAY. The Fed's timeline is a death sentence for small business.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_4", round: 1, action_type: "post", content: "The Fed's mixed messaging — holding rates but promising cuts — is creating a profound disconnect between Main Street pain and Wall Street euphoria. This is a communications failure.", opinion_shift: "neutral" }
      ]
    }
  },
  // 3. Round 2
  {
    type: "round_completed",
    payload: {
      round: 2,
      actions: 5,
      metrics: { opinion_entropy: 1.72, polarization_index: 0.71, gini_coefficient: 0.18, opinion_velocity: 0.35 },
      budget: { total_tokens: 8800, total_cost: 0.0016 },
      sample_actions: [
        { agent_id: "agent_1", round: 2, action_type: "reply", content: "Chloe raises a fair point about communications, but central banking inherently requires balancing these tensions. The dot plot IS the communication — it prevents panic.", opinion_shift: "agree" },
        { agent_id: "agent_0", round: 2, action_type: "reply", content: "The dot plot is a fairy tale, Marcus. They promised cuts earlier this year too and walked it back. Fool me once, shame on you. Fool me twice — that's incompetence.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_3", round: 2, action_type: "post", content: "Elena, the difference is the political calendar. They physically cannot backpedal on 3 cuts entering an election cycle. The liquidity injection is locked in. Period.", opinion_shift: "strongly_agree" },
        { agent_id: "agent_2", round: 2, action_type: "reply", content: "David, I don't care about stock market liquidity. I care about whether I can keep 47 employees on payroll. If they are this incompetent on inflation, I go bankrupt in Q3.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_4", round: 2, action_type: "post", content: "We're seeing severe fracturing. Investors celebrate future liquidity while consumers punish present inaction. The Gini of this debate itself reveals the inequality embedded in Fed policy.", opinion_shift: "neutral" }
      ]
    }
  },
  // 4. Round 3
  {
    type: "round_completed",
    payload: {
      round: 3,
      actions: 5,
      metrics: { opinion_entropy: 1.82, polarization_index: 0.78, gini_coefficient: 0.15, opinion_velocity: 0.28 },
      budget: { total_tokens: 13400, total_cost: 0.0024 },
      sample_actions: [
        { agent_id: "agent_4", round: 3, action_type: "post", content: "After three rounds, the data is clear: this group has polarized further, not converged. The Fed's strategy of 'patience' is interpreted as 'competence' by elites and 'indifference' by everyone else.", opinion_shift: "disagree" },
        { agent_id: "agent_1", round: 3, action_type: "reply", content: "I'll concede one point: the communication strategy has failed. The substance is correct but the packaging has eroded trust. The Fed needs a better narrative, not a different policy.", opinion_shift: "neutral" },
        { agent_id: "agent_0", round: 3, action_type: "reply", content: "Marcus finally admits it. When even the economists say the Fed can't communicate, the public's verdict is already in: incompetent. The next 30 days will be brutal for their approval ratings.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_3", round: 3, action_type: "post", content: "Public sentiment doesn't move markets. Institutional flows do. And institutions are already positioned for cuts. The 'competence' question is irrelevant to anyone with real capital.", opinion_shift: "strongly_agree" },
        { agent_id: "agent_2", round: 3, action_type: "reply", content: "David just proved Chloe's point perfectly. The Fed has created a system where 'competence' is measured entirely by portfolio returns, not by whether working families can afford rent.", opinion_shift: "strongly_disagree" }
      ]
    }
  },
  // 5. Round 4
  {
    type: "round_completed",
    payload: {
      round: 4,
      actions: 5,
      metrics: { opinion_entropy: 1.89, polarization_index: 0.82, gini_coefficient: 0.12, opinion_velocity: 0.18 },
      budget: { total_tokens: 18200, total_cost: 0.0032 },
      sample_actions: [
        { agent_id: "agent_1", round: 4, action_type: "post", content: "I've been tracking the opinion trajectories in this group. We've reached maximum polarization — entropy is near ceiling. This mirrors what I expect to see nationally: a fractured, not unified, response.", opinion_shift: "neutral" },
        { agent_id: "agent_2", round: 4, action_type: "reply", content: "Maximum polarization means maximum pain for people like me caught in the middle. While economists debate entropy curves, I'm looking at my Q3 projections and seeing red.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_0", round: 4, action_type: "post", content: "The Fed will face a reckoning in the next 30 days. Social media sentiment is already turning. Every grocery receipt is a ballot against their competence.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_4", round: 4, action_type: "post", content: "Final synthesis: the Fed's competence perception will split along class lines. Net negative for general public, net positive for institutional investors. The 30-day forecast is bifurcation, not consensus.", opinion_shift: "disagree" },
        { agent_id: "agent_3", round: 4, action_type: "reply", content: "Chloe's bifurcation thesis is exactly right, but I'd add: the institutional positive sentiment will be LOUDER because it controls the media narrative. Headlines will say 'markets confident' while comments say 'incompetent'.", opinion_shift: "agree" }
      ]
    }
  },
  // 5. Round 5
  {
    type: "round_completed",
    payload: {
      round: 5,
      actions: 5,
      metrics: { opinion_entropy: 1.91, polarization_index: 0.85, gini_coefficient: 0.10, opinion_velocity: 0.08 },
      budget: { total_tokens: 23000, total_cost: 0.0042 },
      sample_actions: [
        { agent_id: "agent_4", round: 5, action_type: "post", content: "Final round. The simulation has converged on a clear signal: public sentiment toward the Fed will shift net-negative over 30 days, driven primarily by consumer frustration, despite institutional optimism.", opinion_shift: "disagree" },
        { agent_id: "agent_1", round: 5, action_type: "reply", content: "I reluctantly agree with the directional call. The Fed's substance is sound but their credibility deficit with ordinary Americans is real and will deepen. My confidence in the prediction: 82%.", opinion_shift: "neutral" },
        { agent_id: "agent_0", round: 5, action_type: "post", content: "82%? I'd say 95%. Every person I know thinks the Fed is failing them. This isn't an academic exercise — it's lived reality. The next 30 days will prove us right.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_2", round: 5, action_type: "reply", content: "If three rate cuts actually materialize next year, I might change my mind. But right now? Right now the Fed gets an F from every small business owner I know. Period.", opinion_shift: "strongly_disagree" },
        { agent_id: "agent_3", round: 5, action_type: "post", content: "The market has already priced in the answer. Sentiment is just noise. But I'll give the bears this: the noise matters politically, and that might actually force the Fed's hand earlier than planned.", opinion_shift: "agree" }
      ]
    }
  },
  // 6. Simulation complete
  {
    type: "simulation_ended",
    payload: {
      status: "completed",
      total_actions: 25,
      metrics: { opinion_entropy: 1.91, polarization_index: 0.85, gini_coefficient: 0.10, opinion_velocity: 0.08, final_entropy: 1.91 }
    }
  }
];

export const MOCK_REPORT = `## MURM Analytical Report: Federal Reserve Competence Perception

**Prediction Target:** How will public sentiment shift towards the Fed's competence over the next 30 days?

**Simulation Parameters:** 5 agents · 5 rounds · Forum environment · Normal opinion distribution · Seed 42

---

### 1. Direct Prediction

**Public sentiment toward the Federal Reserve's competence will shift net-negative over the next 30 days, with an estimated 12-18 point decline in general public approval.** However, this decline will be sharply bifurcated along socioeconomic lines: institutional investors and financial professionals will maintain or slightly increase their confidence in the Fed, while consumers, small business owners, and retail investors will register significant drops in perceived competence.

### 2. Evidence from Simulation

The multi-agent simulation produced several key findings across 5 rounds of structured deliberation:

- **Immediate Polarization:** Within the first round, agents split into two distinct camps that never reconverged. The polarization index rose from 0.62 to 0.85 across the simulation, indicating deepening — not moderating — divisions.
- **The "Dot Plot Divide":** The single most contentious element was the Fed's dot plot showing 3 projected rate cuts. Investor-class agents interpreted this as competent forward guidance. Consumer-class agents interpreted it as an empty promise based on prior broken commitments.
- **Communication Failure Consensus:** By Round 3, even the most pro-Fed agent (Marcus Chen, macro-economist) conceded that the Fed's communication strategy had failed, while maintaining that the underlying policy was sound. This nuanced position reflects expert consensus in real-world analysis.
- **Class-Based Perception Split:** Agent Chloe Andersen's Round 4 synthesis crystallized the core finding: "The Fed's competence perception will split along class lines. Net negative for general public, net positive for institutional investors."

### 3. Emergence Analysis

- **Opinion Entropy:** Rose from 1.54 to 1.91 bits across the simulation, indicating increasing diversity of opinion rather than convergence. This suggests the Fed's "wait and see" approach actively generates confusion rather than confidence.
- **Polarization Index:** Climbed steadily from 0.62 to 0.85, confirming that discussion of Fed policy amplifies division rather than building consensus. This has direct implications for social media sentiment analysis.
- **Gini Coefficient:** Dropped from 0.20 to 0.10, meaning participation became more equal over time — all agents were deeply engaged. This suggests the topic has high salience across demographics.
- **Opinion Velocity:** Declined from 0.40 to 0.08, indicating agents locked into their positions quickly. Early impressions of Fed competence are "sticky" and resistant to counter-argument.

### 4. Confidence Assessment

**Confidence Score: 82/100**

The simulation exhibited high internal consistency: the mechanism of sentiment shift (class-based bifurcation driven by communication failure rather than policy substance) was independently identified by multiple agents with different priors. The velocity decline indicates strong agreement on the direction, even while disagreeing on magnitude. Confidence is reduced from 90 to 82 because: (a) the simulation used 5 agents, which limits emergent complexity, and (b) external shocks (geopolitical events, surprise economic data) could override the baseline trajectory.

### 5. Uncertainty Statement

The primary sources of uncertainty are:

- **External Economic Shocks:** A sudden spike in core PCE or an unexpected jobs report within the 30-day window could either accelerate or reverse the predicted sentiment shift.
- **Fed Communication Pivot:** If the Fed issues an unscheduled statement or the Chair gives an interview that directly addresses public frustration, the communication-failure driver could be partially neutralized.
- **Political Amplification:** The proximity to election rhetoric could amplify negative sentiment beyond the simulation's baseline estimate.

Multi-seed variance was low (σ = 0.04 on final entropy), indicating the prediction is robust to initialization differences.

### 6. Limitations

- Population size of 5 agents limits the diversity of perspectives (particularly missing: labor unions, retirees on fixed income, mortgage holders, international investors).
- The Forum environment encourages confrontation; a Town Hall environment might produce different dynamics.
- The simulation does not model real-time information flow from financial media, which could accelerate or dampen sentiment shifts.
- All agents have English-language, US-centric perspectives. International perception of the Fed may diverge significantly.
`;

export const MOCK_COST_ESTIMATE = {
  estimated_cost_usd: 0.0042,
  estimated_total_tokens: 23000,
  total_calls: 25,
  model: "groq/llama-3.3-70b-versatile",
  breakdown: {
    agent_generation: 0.0008,
    simulation_rounds: 0.0028,
    report_generation: 0.0006
  }
};

export const MOCK_DELAY = (ms) => new Promise(r => setTimeout(r, ms));
