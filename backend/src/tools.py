import logging
import os

import httpx
from livekit.agents import RunContext

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

logger = logging.getLogger("tools")


async def web_search_serper(context: RunContext, query: str):
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not configured")
        return "Web search is not configured. Please set SERPER_API_KEY in .env.local"

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5}

    try:
        logger.info(f"Searching web for: {query}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=8.0
            )
            response.raise_for_status()
            results = response.json().get("organic", [])

            if not results:
                return "No relevant results found."

            # Format results
            formatted = []
            for res in results[:5]:
                title = res.get("title", "No title")
                link = res.get("link", "")
                formatted.append(f"• {title}: {link}")

            return "\n".join(formatted)

    except httpx.TimeoutException:
        logger.error("Web search timed out")
        return "Search request timed out. Please try again."
    except httpx.HTTPError as e:
        logger.error(f"Web search HTTP error: {e}")
        return "Search failed due to network error."
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return "Search failed or API unreachable."
