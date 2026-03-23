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

export const MOCK_AGENTS = [
  { agent_id: "agent_0", name: "Elena", description: "A skeptical retail investor highly sensitive to inflation." },
  { agent_id: "agent_1", name: "Marcus", description: "A macro-economist who trusts the Fed's patience." },
  { agent_id: "agent_2", name: "Sarah", description: "A small business owner struggling with high loan rates." },
  { agent_id: "agent_3", name: "David", description: "A day trader entirely focused on the Dot Plot cuts." },
  { agent_id: "agent_4", name: "Chloe", description: "A financial journalist seeking clarity in Fed messaging." }
];

export const MOCK_EVENTS = [
  { type: "agent_generation", content: "Generated Elena: Retail investor" },
  { type: "agent_generation", content: "Generated Marcus: Macro-economist" },
  { type: "agent_generation", content: "Generated Sarah: Small business owner" },
  { type: "agent_generation", content: "Generated David: Day trader" },
  { type: "agent_generation", content: "Generated Chloe: Financial journalist" },
  { type: "round_start", round: 1 },
  { type: "action", agent_id: "agent_1", action: { action: "statement", content: "The Fed is doing exactly what it must. Core inflation hasn't yielded yet; holding rates at 5.25% is prudent.", opinion_shift: "neutral", reasoning: "I believe the Fed is correctly prioritizing long-term stability." } },
  { type: "action", agent_id: "agent_0", action: { action: "objection", content: "Prudent for who? We are being squeezed by these rates and inflation isn't dropping for everyday goods. The Fed is slow.", opinion_shift: "disagree", reasoning: "Retail consumers are suffering under these rates." } },
  { type: "action", agent_id: "agent_3", action: { action: "statement", content: "Ignore the hold, the real news is the 3 cuts on the dot plot! The market is going to rally on that forward guidance.", opinion_shift: "agree", reasoning: "The projection of cuts is all that matters for liquidity." } },
  { type: "action", agent_id: "agent_2", action: { action: "question", content: "Can my business survive another year of this? 'Next year' is too far away for payroll loans right now.", opinion_shift: "strongly_disagree", reasoning: "High borrowing costs are squeezing my margins today." } },
  { type: "action", agent_id: "agent_4", action: { action: "statement", content: "The Fed's mixed messaging—holding rates but promising cuts—is creating a profound disconnect between main street and wall street.", opinion_shift: "neutral", reasoning: "Journalistic observation of the growing polarization." } },
  { type: "round_end", round: 1 },
  { type: "round_start", round: 2 },
  { type: "action", agent_id: "agent_1", action: { action: "statement", content: "Chloe raises a fair point, but central banking requires balancing those precise tensions. The dot plot prevents panic.", opinion_shift: "agree", reasoning: "Defending the dual-mandate approach." } },
  { type: "action", agent_id: "agent_0", action: { action: "strongly_disagree", content: "The dot plot is a fairy tale. They promised cuts earlier this year too! Absolute incompetence.", opinion_shift: "strongly_disagree", reasoning: "Loss of trust in Federal Reserve forward guidance." } },
  { type: "action", agent_id: "agent_3", action: { action: "support", content: "They won't backpedal on 3 cuts entering an election cycle next year. The liquidity is coming, period.", opinion_shift: "strongly_agree", reasoning: "Political and market pressures enforce the rate cuts." } },
  { type: "action", agent_id: "agent_2", action: { action: "statement", content: "I don't care about the stock market liquidity. I care about my debt servicing. If they are incompetent on inflation, I go bankrupt.", opinion_shift: "strongly_disagree", reasoning: "Reiterating the real-world consequence of Fed policy delay." } },
  { type: "action", agent_id: "agent_4", action: { action: "statement", content: "We are seeing severe fracturing in consensus here. Investors celebrate the future, while consumers punish the present.", opinion_shift: "neutral", reasoning: "Synthesizing the debate's core conflict." } },
  { type: "round_end", round: 2 },
  { type: "simulation_complete" }
];

export const MOCK_METRICS = [
  { round: 1, entropy: 1.54, polarization: 0.62, gini: 0.20, velocity: 0.40 },
  { round: 2, entropy: 1.82, polarization: 0.78, gini: 0.15, velocity: 0.25 }
];

export const MOCK_REPORT = `## MURM Analytical Report: Federal Reserve Competence
**Prediction Target:** How will public sentiment shift towards the Fed's competence over the next 30 days?
**Extracted Concept Map:** 7 Nodes, 7 Edges

### 1. Direct Prediction
**Public sentiment over the next 30 days will bifurcate sharply, resulting in an overall negative shift regarding Fed competence from the general public, offset only by targeted approval from the investor class.** 

### 2. Evidence from Simulation
During the multi-agent simulation spanning 2 discussion rounds, a stark divergence materialized immediately:
*   **The Main Street Pain Point:** Agents representing retail investors and small businesses (Elena, Sarah) immediately shifted toward \`strongly_disagree\`, citing current debt servicing costs and immediate inflation pain. 
*   **The Wall Street Buffer:** Agents representing macro-economics and day-trading (Marcus, David) anchored fully on the "Dot Plot", viewing the promise of 3 cuts as competent forward guidance.

### 3. Emergence Analysis
* **Polarization Spike:** The divergence score jumped from 0.62 to 0.78 by Round 2. The Fed's attempt to thread the needle (hold rates now, cut later) explicitly fueled this polarization.
* **Loss of Trust Baseline:** Agent 0 specifically cited previous broken promises regarding rate cuts. This indicates that the 30-day sentiment will be driven by *cynicism toward the Dot Plot* rather than the actual 5.25% rate hold itself.

### 4. Confidence Assessment (82/100)
The simulation exhibited high consensus on the mechanism of the shift (the disconnect between present pain and future promises). The confidence score holds at 82 because the arguments mapped perfectly to current macroeconomic realities, showing low entropy in the final opinion states.

### 5. Uncertainty Statement
The primary variable representing uncertainty is whether an external macroeconomic shock (like a sudden spike in core PCE) occurs within the 30-day window, which would invalidate the highly-anchored Dot Plot narrative and unify all demographics against the Fed's competence.
`;

export const MOCK_DELAY = (ms) => new Promise(r => setTimeout(r, ms));
