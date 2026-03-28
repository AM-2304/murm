# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-03-28

### Added
- **LLM-Powered News Grounding**: Upgraded the news injection pipeline to use LLM-based keyword extraction. This ensures search queries are hyper-relevant to the simulation topic (e.g., specific supply chain disruptions rather than generic news).
- **Live Knowledge Graph Updates**: God Mode event injections now trigger background graph extraction. Injected entities and relations are automatically appended to the project's Knowledge Graph and Vector Store mid-simulation.
- **Cross-Agent Interaction**: Implemented direct agent-to-agent replies. Agents can now tag and respond to each other (e.g., `Reply to @Name`), enabling deeper multi-party deliberation.
- **Robust Agent Persistence**: Added detailed error tracking and fallback serialization for `agents.json`, ensuring agent states are always saved for post-simulation interviews even if LLM outputs are malformed.

### Changed
- **CLI Compatibility**: Restored single-dash aliases (`-port`, `-host`, etc.) to support legacy workflows alongside standard POSIX flags.
- **Real-Time News API Integration**: MURM now supports live news grounding via GNews, NewsData.io, and NewsAPI.org. Set `NEWS_PROVIDER` and `NEWS_API_KEY` in `.env` to activate. Falls back to Wikipedia (zero-config) when no key is configured.
- **Geographic Persona Generation**: Agent demographics are now context-aware. If a specific country or region is mentioned in the prediction question, agents are generated with culturally appropriate names, locations, and backgrounds.
- **Report Engine Redesign**: Complete rewrite of `report_agent.py` to produce high-quality intelligence briefs with numbered findings, evidence blockquotes, and quantitative dashboards.
- **Grounding Visibility**: Agent prompts now explicitly separate pinned breaking news from regular discussion feed, ensuring real-world context is always visible.
- **Provider Architecture**: `web.py` rewritten with a provider-agnostic dispatcher pattern supporting pluggable news sources.

## [0.4.3] - 2026-03-27

### Fixed
- **Agent Output Truncation**: Increased the token limit (300 to 800) and character limits across the simulation engine (`engine.py`) to prevent agent responses and context from being truncated during live simulation feeds.
- **Static Analysis Import Errors**: Resolved IDE local import issues (`Could not find import`) by adding a properly configured `pyrightconfig.json` to define search roots, virtual environment paths, and explicitly typing asyncio gather results.

## [0.4.2] - 2026-03-26

### Fixed
- **Indexing Error**: Resolved the critical `Cannot index into list[str]` type error in `murm/simulation/web.py` by transitioning all list slicing to the more robust `itertools.islice()` mechanism, ensuring cross-version compatibility for type checkers and runtimes.

## [0.4.1] - 2026-03-26

### Added
- **Expert Analysis Mode**: The simulation now ships with a fully discrete, multi-step thesis-generation report mode by default.
- **Agent Interview Mode**: Added global capability to interview simulation agents seamlessly mapped to `agents.json`.
- **D3 Graph Exporter**: Fully integrated `[DOWNLOAD SVG]` component into the knowledge graph renderer for pitch-ready visualizations.

### Fixed
- **Simulation Stalls**: Fixed the critical `ctx_text` prompt building crash and resolved probabilistic action throttling causing "0 action" drops.
- **Entropy & Opinion Flattening**: Drastically overhauled keyword extraction with forced syntax tagging (`[AGREE]`, `[DISAGREE]`), elevating opinion shift capture to 100%. 
- **Report & UI Decorators**: Implemented extremely restrictive LLM instructions to universally block bullet asterisks (`**`) and stylistic emojis across normal and expert regimes.
- **Graph UX**: React Graph Legend panel is now cleanly wrapped with vertical overflow to support mass-entity extraction.
- **Brier Score UX**: Labeled Brier accuracy dynamically to stipulate requirement for ground-truth convergence.
