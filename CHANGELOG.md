# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-03-25

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
