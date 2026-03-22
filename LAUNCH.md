# LAUNCH STRATEGY: Getting MURM in Front of People Who Will Use It

## The realistic sequence

Do not post everywhere on day one. Credibility compounds when you post somewhere,
get traction, then reference that traction when posting the next place. The sequence
below is ordered by effort-to-impact ratio.

---

## Week 1: Establish the foundation before posting anywhere

Before you share a single link, make sure these are in place:

1. GitHub repository is public with a complete README
2. At least one real demo run documented with actual output (a screenshot of the
   dashboard, a saved report.md showing a real prediction)
3. PyPI package is live and installable with one command
4. A short demo video (even 2 minutes of screen recording) uploaded to YouTube or
   stored as a GitHub release asset

Tools for the demo video: Loom (free, records screen + voiceover, instant shareable link).
You do not need to edit it. A raw recording of you running the tool and explaining
what it does as you go is more trustworthy than a polished promo.

---

## Venue 1: Hacker News (highest signal-to-noise, most developer reach)

**What it is:** A community of technical people — researchers, engineers, founders —
who read and discuss software projects, papers, and ideas. A front-page post here
can bring 10,000-50,000 visitors in 24 hours.

**How to post:**

Go to news.ycombinator.com and create an account. Wait at least one day after
account creation before posting (brand-new accounts get less traction).

Click "Submit" and use this title format:
```
Show HN: MURM – simulate public opinion with local LLMs, no cloud services required
```

The "Show HN" prefix is the standard format for projects you have built. Use it.

In the text box, write 3-5 sentences maximum:
```
MURM is an open-source tool that predicts public sentiment by simulating
a diverse population of autonomous agents reacting to a seed document.

It is a local-first, English-language improvement on MiroFish (33k GitHub stars,
Chinese-only). Key differences: no Zep Cloud dependency, works with any LLM provider,
enforces statistical opinion diversity to prevent herd behavior, and produces
calibrated predictions with uncertainty bounds.

Install: pip install murm
GitHub: [link]
```

**When to post:** Tuesday or Wednesday, between 9am-12pm US Eastern time. This is
when the most active Hacker News readers are online.

**What to expect:** If your post gets 10+ upvotes in the first hour it will appear
on the front page. Respond to every comment within the first 4 hours — engagement
signals quality to the algorithm.

---

## Venue 2: r/LocalLLaMA and r/MachineLearning (Reddit)

**What they are:** Large communities of ML practitioners who closely follow open-source
AI tools. r/LocalLLaMA has 200k+ members focused on running AI locally.

**r/LocalLLaMA post:**
```
Title: Built a local-first public opinion simulator — simulate how crowds react to
any document, no cloud needed

Body:
I built MURM after being frustrated by MiroFish (a similar Chinese tool with
33k stars but: requires Zep Cloud, Chinese-only, agents all cluster to neutral).

What it does: you feed it a document, ask a question ("how will people react to this
policy?"), and it simulates a population of diverse agents discussing it. All local,
works with Ollama.

Key technical differences from MiroFish:
- NetworkX + ChromaDB instead of Zep Cloud (fully local, zero cost)
- Live Wikipedia Context Grounding + Real-time Dynamic GraphRAG visualization
- Deeply-seeded demographic archetypes + quota-sampled opinion distribution (fixes agent herd behavior)
- Shannon entropy and polarization index per round (actual emergence metrics)
- Multi-seed sensitivity analysis + post-simulation A/B Counterfactual branching

GitHub: [link] | pip install murm
```

**r/MachineLearning post:**
```
Title: [Project] MURM: open-source swarm intelligence prediction with
calibrated uncertainty bounds and emergence metrics

Body:
[Link to GitHub]

I built this as a research-grade alternative to MiroFish. The key research
contribution is treating swarm prediction as a calibrated forecasting problem:
predictions come with Brier score infrastructure, multi-seed sensitivity analysis,
and Shannon entropy/polarization metrics that quantify emergence rather than just
returning a narrative.

The agent diversity problem (LLM agents polarizing faster than real humans, documented
in the OASIS paper) is addressed via quota-sampled population initialization.

Happy to discuss the design decisions.
```

---

## Venue 3: X / Twitter

Two types of posts work: threads and screenshots.

**Thread format (post this as a thread, each point is one tweet):**

Tweet 1:
```
I built an open-source tool that predicts public sentiment by simulating crowds of
AI agents reacting to any document.

Local-first. Works with @OpenAI, @AnthropicAI, Groq, or local Ollama.
No cloud database required.

pip install murm
github.com/[your handle]/murm

[screenshot of the live metrics dashboard]
```

Tweet 2:
```
The problem with existing tools like MiroFish (33k GitHub stars):

- Requires Zep Cloud account and only Chinese interfaces
- Static graphs and no real-world context grounding
- All agents converge to neutral (herd behavior — documented in the OASIS paper)
- Single prediction, no confidence bounds or A/B timeline comparison

Thread on how we fixed each one...
```

Tweet 3:
```
1/ Herd behavior fix

Ask an LLM to "generate 50 diverse people" and they all start mildly neutral
and quickly agree with each other.

We pre-assign every agent's starting opinion using quota sampling before a single
LLM call is made. Same math used in electoral polling to enforce demographic targets.
```

Continue for the other key improvements. End with:
```
All 44 tests pass. MIT license. PR contributions welcome.

pip install murm | github.com/[handle]/murm

[demo video link]
```

**Who to tag (only if genuinely relevant to their work):**
- Researchers who have published on LLM agent simulation
- Open-source AI community accounts you already follow

Do not tag random famous people. It looks desperate and gets ignored.

---

## Venue 4: GitHub itself

**Add repository topics:**

Go to your repository > click the gear icon next to "About" > add these topics:
```
multi-agent, simulation, swarm-intelligence, prediction, llm, python,
public-opinion, social-simulation, knowledge-graph, sentiment-analysis
```

These are searchable. People browsing these topics will find the repository
independently without you doing anything.

**List on Awesome lists:**

Search GitHub for "awesome-llm-agents" and similar curated lists. Many have
instructions for submitting a PR to add your project. The PR title format is
usually `Add [project name] - [one line description]`.

**Star network:**

Ask 5-10 people you know who work in AI or software to star the repository in the
first week. Not for vanity — GitHub's trending algorithm gives significantly more
weight to recent stars, so a small burst of stars on day one can land you on the
"Trending Python repositories" list, which generates thousands of organic visitors.

---

## Venue 5: Discord communities

These communities have real-time channels for sharing projects and getting feedback:

- **Latent Space Discord** (latent.space/discord) — AI practitioner community,
  active #projects channel
- **EleutherAI Discord** — open-source AI research focused
- **LlamaIndex Discord** — RAG and knowledge graph practitioners
- **CAMEL-AI Discord** — directly relevant since MURM is an alternative
  to their OASIS framework

In all of these: introduce yourself briefly, post the GitHub link with a one-sentence
description, offer to answer questions. Do not paste a marketing pitch.

---

## Venue 6: ArXiv (for research credibility)

The `paper/paper.tex` file in the repository is a complete academic paper scaffold.
Once you have run the benchmarks and filled in your experimental results:

1. Compile it to PDF: `pdflatex paper.tex && bibtex paper && pdflatex paper.tex`
2. Upload to arXiv.org (free, takes 1-2 days to be listed)
3. Choose category: cs.SI (Social and Information Networks) or cs.AI (Artificial Intelligence)

Once the arXiv paper is live, every subsequent post can include the line:
"Technical paper: arxiv.org/abs/[your ID]"

This transforms the project from a tool to a research contribution. A significant
portion of the ML community will not engage seriously with a tool unless there is
a paper attached.

---

## Venue 7: Product Hunt (for broader visibility)

Product Hunt is a website where new products are featured daily. It is less
technical than Hacker News but reaches a broader audience including journalists,
investors, and non-technical users.

1. Create an account at producthunt.com
2. Click "Submit" > fill in the details
3. Use a clear screenshot of the dashboard as the thumbnail
4. Post on a Tuesday, Wednesday, or Thursday
5. Ask your network to upvote it on launch day (the first 4 hours determine ranking)

---

## Response template for when people ask "how is this different from MiroFish"

```
MiroFish is the project this was built to improve on. Specific differences:

Technical:
- No Zep Cloud dependency (local NetworkX + ChromaDB instead)
- Works with any LLM via LiteLLM (OpenAI, Anthropic, Groq, Ollama, 100+ others)
- Fully async FastAPI instead of synchronous Flask
- SQLite state persistence (survives server restarts)

Research quality:
- Real-world Wikipedia grounding injected at simulation start
- Dynamic GraphRAG that physically evolves on-screen as agents chat
- Enforced opinion diversity via demographic archetype seeding and quota sampling
- Per-round emergence metrics: Shannon entropy, Gini, polarization index
- Multi-seed sensitivity analysis + 1-click A/B timeline comparison
- Seeded randomness for reproducibility

Usability:
- English throughout (MiroFish is Chinese-only)
- CLI and Python SDK (MiroFish is UI-only)
- DELETE endpoints for cleanup
- skip_graph flag for quick runs
- Pre-flight cost estimates

44 tests pass, MIT license, pip install murm
```

---

## What to track to know if it is working

- GitHub stars (aim for 100 in week 1 if the Hacker News post lands)
- PyPI download count (visible at pypistats.org/packages/murm)
- GitHub Issues opened (each one is a real person engaging with the project)
- Forks (researchers forking it to run experiments on their own data)

The single best signal that the project has found its audience is when someone
you have never heard of opens a GitHub Issue or submits a Pull Request.
