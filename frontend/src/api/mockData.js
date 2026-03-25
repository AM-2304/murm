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
      metrics: { opinion_entropy: 1.54, polarization_index: 0.62, gini_coefficient: 0.20, opinion_velocity: 0.40, dominant_opinion: "disagree", consensus: 0.20, activity_rate: 1.0 },
      budget: { total_tokens: 4200, estimated_cost_usd: 0.0008, budget_used_pct: 19 },
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
      metrics: { opinion_entropy: 1.72, polarization_index: 0.71, gini_coefficient: 0.18, opinion_velocity: 0.35, dominant_opinion: "strongly_disagree", consensus: 0.25, activity_rate: 1.0 },
      budget: { total_tokens: 8800, estimated_cost_usd: 0.0016, budget_used_pct: 38 },
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
      metrics: { opinion_entropy: 1.82, polarization_index: 0.78, gini_coefficient: 0.15, opinion_velocity: 0.28, dominant_opinion: "strongly_disagree", consensus: 0.28, activity_rate: 1.0 },
      budget: { total_tokens: 13400, estimated_cost_usd: 0.0024, budget_used_pct: 57 },
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
      metrics: { opinion_entropy: 1.89, polarization_index: 0.82, gini_coefficient: 0.12, opinion_velocity: 0.18, dominant_opinion: "disagree", consensus: 0.22, activity_rate: 1.0 },
      budget: { total_tokens: 18200, estimated_cost_usd: 0.0032, budget_used_pct: 79 },
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
      metrics: { opinion_entropy: 1.91, polarization_index: 0.85, gini_coefficient: 0.10, opinion_velocity: 0.08, dominant_opinion: "disagree", consensus: 0.20, activity_rate: 1.0 },
      budget: { total_tokens: 23000, estimated_cost_usd: 0.0042, budget_used_pct: 100 },
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
      metrics: { opinion_entropy: 1.91, polarization_index: 0.85, gini_coefficient: 0.10, opinion_velocity: 0.08, final_entropy: 1.91, dominant_opinion: "disagree", consensus: 0.20, activity_rate: 1.0 }
    }
  }
];

export const MOCK_BASIC_REPORT = `## Definition of the Prediction Target
Prediction Target: How will public sentiment shift towards the Fed's competence over the next 30 days?

Simulation Parameters: 5 agents · 5 rounds · Forum environment · Normal opinion distribution · Seed 42

--

## Prediction
Public sentiment toward the Federal Reserve's competence will shift net-negative over the next 30 days, resulting in a substantial and highly visible decline in general public approval. However, the simulation indicates this decline will be sharply bifurcated along socioeconomic lines. Institutional investors and financial professionals will maintain or slightly increase their confidence in the Fed, interpreting the Dot Plot as rational forward guidance. In stark contrast, consumers, small business owners, and retail investors will register significant drops in perceived competence, driven by immediate financial distress and historical distrust.

## Evidence & Quantitative Dynamics
The simulation provided compelling evidence of this trajectory through its metrics. Opinion Entropy rose from 1.54 bits to 1.91 bits, approaching the theoretical maximum. This indicated that the crowd was not converging on a single shared reality, but rather fragmenting into mutually exclusive camps. Polarization skyrocketed from 0.62 to 0.85, confirming that the agent's interaction deepened existing divides. 

Specifically, agent Sarah Okonkwo repeatedly anchored to her immediate financial reality ("my employees are gone"), completely rejecting the forward-looking signals of agent Marcus Chen, who focused on the Dot Plot. The opinion velocity dropped from 0.40 to 0.08 by Round 5, signaling that these polarized positions hardened quickly and became entirely resistant to new data or counter-arguments.

## Emergence Analysis & Turning Points
The simulation demonstrated a complex dynamic of "Discursive Deadlock". Initially, institutional agents attempted to sway consumer agents using macroeconomic projections. However, the critical turning point arrived in Round 3, when agent Chloe Andersen noted the communications failure. This broke the institutional echo chamber and validated the consumer frustration. There was no consensus formed; instead, the collective dynamically split into a permanent, intractable two-faction system.

## Confidence Assessment
Score: 82

This score is justified by the extremely high internal consistency of the simulated run. The velocity decline indicates strong agreement on the trajectory, and the structural causes (class-based realities) are deeply embedded. The score stops short of 90 because the limited agent pool size (N=5) creates minor margin for systemic variance.

## Limitations & Edge Cases
The simulation is bounded by the current macro environment. An exogenous shock—such as an unexpected geopolitical energy crisis or a catastrophic jobs report—could completely alter this trajectory, forcing the Fed into an emergency cut that would break the identified paradigm. Additionally, irrational viral social media movements were not modeled, which could amplify negative sentiment beyond the 82% confidence threshold.
`;

export const MOCK_EXPERT_REPORT = `## MURM Intelligence Report: Federal Reserve Competence Perception

Prediction Target: How will public sentiment shift towards the Fed's competence over the next 30 days?

Simulation Parameters: 5 agents · 5 rounds · Forum environment · Normal opinion distribution · Seed 42

--

## Executive Summary
The simulation indicates a high probability that public sentiment toward the Federal Reserve will sour significantly over the next thirty days. This decline will not be uniform; it will manifest as a severe, class-based bifurcation. While institutional players will view the Fed's "higher for longer" stance and forward dot-plot guidance as highly competent and necessary, the general public and small-business sector will interpret the exact same data as evidence of catastrophic detachment. 

## Key Themes & Findings
1. The "Two Realities" Disconnect: Macroeconomic projections are actively rejected by agents facing immediate microeconomic distress.
2. The Limits of Forward Guidance: Future promises (the Dot Plot) hold zero persuasive value for actors experiencing present insolvency.
3. Communication Over Substance: The Fed's policy substance was largely agreed upon by experts, but the communication strategy was universally condemned as inadequate for Main Street.

## Deep Evidence & Metrics Breakdown
The quantitative emergence metrics paint a stark picture of failure to achieve consensus. 
* **Opinion Entropy (1.54 -> 1.91):** The crowd fragmented. Instead of coming together, agents explored the absolute extremes of the opinion spectrum.
* **Polarization Index (0.62 -> 0.85):** The divergence was not minor; it was structural. The population physically split into bimodal camps that refused to integrate.
* **Opinion Velocity (0.40 -> 0.08):** By Round 4, opinions were entirely locked. Agents stopped listening to each other and simply shouted their pre-existing anchors.

## Discourse & Influencer Analysis
The discourse was initially driven by institutional figures like Marcus Chen, who attempted to establish the narrative using the Dot Plot. However, the narrative control was violently seized in Round 2 by Sarah Okonkwo (the small business owner). Her appeals to immediate payroll realities acted as memetic contagion, forcing even neutral observers like the journalist (Chloe Andersen) to concede that the Fed's communication had failed. This was the critical turning point that cemented the negative trajectory.

## Contextual Grounding & Entity Impact
The local knowledge graph perfectly grounded this dispute. The relationship between "Federal Reserve" -> "Interest Rates" was weaponized by the "Consumers" generic grouping. The text's citation of "Core Inflation" was utilized by the experts to justify patience, but ignored entirely by the consumers who focused purely on "Public Sentiment" and immediate liquidity.

## Impact of Theoretical Interventions
Baseline operations ran without God Mode injection, proving that the system naturally tends toward hostility on this topic. If a "Surprise 50bps Cut" were injected conceptually, the metrics suggest institutional agents would rebel, flipping the polarization dynamic entirely. 

## Leading Indicators & Warning Signs
To track this in reality, analysts must watch the spread between consumer confidence indices and the S&P 500. A widening gap in these two metrics over the next 14 days will serve as absolute confirmation of this simulation's bifurcated prediction.

## Actionable Takeaways & Strategic Suggestions
* **For Institutional Investors:** Ignore retail sentiment indicators; they will flash red but will not alter Fed policy timelines.
* **For Policymakers:** Immediately pivot communication strategies to acknowledge microeconomic pain. Do not rely on the Dot Plot in consumer-facing messaging.

## Confidence Assessment & Limitations
Score: 86

The confidence in the bifurcation prediction is immensely high due to the structural lockdown observed in the opinion velocity metrics. However, the simulation intentionally restricts the population size, failing to capture the potential mitigating effects of highly targeted regional fiscal policies or the noise introduced by the upcoming election cycle, lowering the score slightly from absolute certainty.
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
