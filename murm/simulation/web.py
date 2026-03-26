from __future__ import annotations
import logging
import asyncio
import httpx
import itertools

logger = logging.getLogger(__name__)

_OFFLINE_MODE = False

async def fetch_real_world_context(query: str, max_words: int = 100) -> str | None:
    global _OFFLINE_MODE
    if _OFFLINE_MODE:
        return None
    """
    Fetches real-world factual context from Wikipedia to ground the simulation.
    Uses the public MediaWiki API. No auth required.
    """
    if not query or len(query) < 3:
        return None

    # Clean query of common stop words for better Wikipedia hits
    search_term = query.replace("?", "").replace("!", "").strip()
    words = search_term.split()
    if len(words) > 5:
        # Just use the first few significant words if it's a long sentence
        filtered_words = [w for w in words if len(w) > 3]
        search_term = " ".join(itertools.islice(filtered_words, 3))

    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": search_term,
        "utf8": "1",
        "srlimit": 1
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            search_res = await client.get(url, params=params)
            search_data = search_res.json()
            
            if not search_data.get("query", {}).get("search"):
                return None
                
            first_hit = search_data["query"]["search"][0]
            title = first_hit["title"]
            
            # Now fetch the extract for this specific title
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "titles": title
            }
            ext_res = await client.get(url, params=extract_params)
            ext_data = ext_res.json()
            
            pages = ext_data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "extract" in page_info:
                    text = page_info["extract"].replace("\n", " ").strip()
                    # Truncate to word limit
                    words = text.split()
                    truncated = " ".join(itertools.islice(words, max_words))
                    return f"Real-world fact ({title}): {truncated}..."
                    
    except Exception as e:
        logger.debug(f"Web search failed for query '{query}': {e}")
        _OFFLINE_MODE = True
        
    return None
