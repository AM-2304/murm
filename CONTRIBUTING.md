# Contributing to MURM

## Development setup

```bash
git clone https://github.com/AM-2304/murm
cd murm
pip install -e ".[dev]"
cp .env.example .env
```

Set at minimum `LLM_API_KEY` and `LLM_MODEL` in `.env`. Any LiteLLM-compatible model string works.

## Running tests

```bash
python -m pytest tests/ -v
```

The test suite covers all deterministic components and requires no LLM API key. Tests that invoke the LLM are integration tests and are not part of the default suite.

## Code style

```bash
python -m ruff check murm/
python -m ruff format murm/
```

## Project structure for contributors

Each module has a single responsibility. The dependency graph flows strictly downward:

```
config.py
  ↓
llm/ (provider, budget)
  ↓
graph/ (engine, embedder, extractor)
agents/ (model, generator)
  ↓
simulation/ (engine, environment, metrics, trace)
  ↓
analysis/ (report_agent, calibration)
  ↓
api/ (store, app, routes)
cli.py
```

Nothing in `simulation/` imports from `api/`. Nothing in `graph/` imports from `agents/`. Circular imports will break the test suite.

## Adding a new environment

Create a class in `murm/simulation/environment.py` that extends `Environment` and implements three methods:

```python
class MyEnvironment(Environment):
    def get_context_feed(self, round_num: int, max_items: int = 10) -> list[str]: ...
    def ingest_action(self, action: dict) -> None: ...
    def inject_external_event(self, content: str, source: str, round_num: int) -> None: ...
    def get_all_posts(self) -> list[dict]: ...
```

Register it in the `build_environment()` factory dict.

## Adding a new emergence metric

Add a function to `murm/simulation/metrics.py` following the pattern of the existing helpers. Call it inside `MetricsCollector.record_round()` and include the result in the returned dict. Add a corresponding test in `tests/test_core.py`.

## Pull request checklist

- [ ] All existing tests pass (`pytest tests/`)
- [ ] New functionality has tests
- [ ] No circular imports introduced
- [ ] No hardcoded API keys, model names, or file paths
- [ ] Comments in English only
- [ ] No emojis in code or comments

## Reporting issues

Please include: OS, Python version, LLM provider and model, the exact error message, and the minimum seed text that reproduces the issue. Issues without reproduction steps will be triaged last.
