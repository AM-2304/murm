"""
Real-world context grounding for MURM simulations.

Supports multiple news/knowledge providers:
  - gnews:     Google News headlines via GNews API (recommended, free tier)
  - newsdata:  NewsData.io articles (free tier, 200 req/day)
  - newsapi:   NewsAPI.org headlines (free tier, dev-only)
  - wikipedia: MediaWiki extracts (zero-config fallback, no key needed)

Provider is selected via NEWS_PROVIDER env var. Falls back to Wikipedia
if no NEWS_API_KEY is set, ensuring zero-config always works.
"""

from __future__ import annotations

import itertools
import logging

import httpx
from murm.config import settings

logger = logging.getLogger(__name__)

_OFFLINE_MODE = False


def _get_provider() -> str:
    """Determine news provider from centralized settings."""
    provider = settings.news_provider.lower().strip()
    api_key = settings.news_api_key
 
    if provider and api_key:
        return provider
    if api_key and not provider:
        return "gnews"  # default if key is set but no provider specified
    return "wikipedia"  # zero-config default


async def fetch_real_world_context(query: str, max_words: int = 120) -> str | None:
    """
    Fetch real-world context to ground the simulation.
    Dispatches to the configured provider.
    """
    global _OFFLINE_MODE
    if _OFFLINE_MODE:
        return None

    if not query or len(query) < 3:
        return None

    provider = _get_provider()
    try:
        if provider == "gnews":
            return await _fetch_gnews(query, max_words)
        elif provider == "newsdata":
            return await _fetch_newsdata(query, max_words)
        elif provider == "newsapi":
            return await _fetch_newsapi(query, max_words)
        else:
            return await _fetch_wikipedia(query, max_words)
    except Exception as e:
        logger.debug("News fetch failed (provider=%s): %s", provider, e)
        # Try Wikipedia as ultimate fallback before going offline
        if provider != "wikipedia":
            try:
                return await _fetch_wikipedia(query, max_words)
            except Exception:
                pass
        _OFFLINE_MODE = True
        return None



# Provider: GNews 

async def _fetch_gnews(query: str, max_words: int) -> str | None:
    """Fetch top headline from GNews API (gnews.io)."""
    api_key = settings.news_api_key or ""
    search_term = await _clean_query(query)

    url = "https://gnews.io/api/v4/search"
    params = {
        "q": search_term,
        "lang": "en",
        "max": 3,
        "apikey": api_key,
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        res = await client.get(url, params=params)
        data = res.json()

    articles = data.get("articles", [])
    if not articles:
        return None

    # Combine top headlines into a grounding context
    headlines = []
    for article in list(itertools.islice(articles, 3)):
        title = article.get("title", "")
        desc = article.get("description", "")
        source = article.get("source", {}).get("name", "News")
        if title:
            snippet = f"{title}. {desc}" if desc else title
            words = snippet.split()
            truncated = " ".join(itertools.islice(words, max_words))
            headlines.append(f"[{source}] {truncated}")

    if not headlines:
        return None

    return "Breaking news context: " + " | ".join(headlines)


# Provider: NewsData.io


async def _fetch_newsdata(query: str, max_words: int) -> str | None:
    """Fetch latest articles from NewsData.io."""
    api_key = settings.news_api_key or ""
    search_term = await _clean_query(query)

    url = "https://newsdata.io/api/1/latest"
    params = {
        "q": search_term,
        "language": "en",
        "size": 3,
        "apikey": api_key,
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        res = await client.get(url, params=params)
        data = res.json()

    results = data.get("results", [])
    if not results:
        return None

    headlines = []
    for article in list(itertools.islice(results, 3)):
        title = article.get("title", "")
        desc = article.get("description", "")
        source = article.get("source_id", "News")
        if title:
            snippet = f"{title}. {desc}" if desc else title
            words = snippet.split()
            truncated = " ".join(itertools.islice(words, max_words))
            headlines.append(f"[{source}] {truncated}")

    if not headlines:
        return None

    return "Latest news context: " + " | ".join(headlines)


# Provider: NewsAPI.org


async def _fetch_newsapi(query: str, max_words: int) -> str | None:
    """Fetch headlines from NewsAPI.org (free tier: dev only)."""
    api_key = settings.news_api_key or ""
    search_term = await _clean_query(query)

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": search_term,
        "language": "en",
        "pageSize": 3,
        "sortBy": "publishedAt",
    }
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient(timeout=8.0) as client:
        res = await client.get(url, params=params, headers=headers)
        data = res.json()

    articles = data.get("articles", [])
    if not articles:
        return None

    headlines = []
    for article in list(itertools.islice(articles, 3)):
        title = article.get("title", "")
        desc = article.get("description", "")
        source = article.get("source", {}).get("name", "News")
        if title:
            snippet = f"{title}. {desc}" if desc else title
            words = snippet.split()
            truncated = " ".join(itertools.islice(words, max_words))
            headlines.append(f"[{source}] {truncated}")

    if not headlines:
        return None

    return "News intelligence: " + " ".join(headlines)


# Provider: Wikipedia (zero-config fallback)


async def _fetch_wikipedia(query: str, max_words: int) -> str | None:
    """Fetch factual context from Wikipedia. No API key required."""
    search_term = await _clean_query(query)

    url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": search_term,
        "utf8": "1",
        "srlimit": 1,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        search_res = await client.get(url, params=search_params)
        search_data = search_res.json()

        if not search_data.get("query", {}).get("search"):
            return None

        title = search_data["query"]["search"][0]["title"]

        extract_params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": title,
        }
        ext_res = await client.get(url, params=extract_params)
        ext_data = ext_res.json()

        pages = ext_data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if "extract" in page_info:
                text = page_info["extract"].replace("\n", " ").strip()
                words = text.split()
                truncated = " ".join(itertools.islice(words, max_words))
                return f"Real-world fact ({title}): {truncated}..."

    return None


# Helpers


async def _clean_query(query: str) -> str:
    """Use an LLM to extract highly relevant search keywords from the scenario."""
    try:
        from murm.llm.provider import AgentLLMProvider
        
        prompt = (
            f"Extract a concise news search query (3-5 core keywords max) for the following topic: {query}\n"
            "Exclude placeholder verbs and interrogatives (will, does, what, how, if).\n"
            "Include ONLY the core entities, actors, and the specific event.\n"
            "Return NOTHING but the space-separated keywords."
        )
        llm = AgentLLMProvider() # using basic provider to not burn trackable budget
        res = await llm.complete([{"role": "user", "content": prompt}], max_tokens=15, temperature=0.0)
        clean = res.strip().replace('"', '').replace("'", "")
        return clean if len(clean.split()) <= 6 else query[:40]
    except Exception as e:
        logger.debug("Failed to extract LLM query keywords, falling back: %s", e)
        search_term = query.replace("?", "").replace("!", "").strip()
        words = search_term.split()
        if len(words) > 5:
            # strip common English stopwords simply to improve fallback
            stops = {"will", "how", "what", "is", "are", "do", "does", "the", "a", "an", "and", "or"}
            filtered = [w for w in words if len(w) > 2 and w.lower() not in stops]
            search_term = " ".join(itertools.islice(filtered, 4))
        return search_term
