import asyncio
from pathlib import Path

from .indexes import make_index


# These settings apply to both attempts; neither may use paid tools or browsers.
FREE_SEARCH_OPTIONS = {
    "action_classes": ("READ_PUBLIC",),
    "provider": "http",
    "allow_paid_fallbacks": False,
    "allow_local_browser": False,
    "allow_real_browser": False,
    "search_source_allow": ("searxng", "duckduckgo_html"),
    "search_paid_parallel": False,
    "search_date_reads": 0,
    "provider_max_attempts_per_candidate": 1,
    "completeness_escalation": False,
    "use_egress_pool": False,
    "rescue_not_found": False,
    "sign_requests": False,
}


async def search_source(web, query: str, source: str, engine_config: dict | None) -> dict:
    """Send one search request and return the source's answer unchanged."""
    import frankensurf as fs

    # Allow the fixed local SearXNG service; keep the private-network guard for DuckDuckGo.
    policy = fs.WebPolicy(**FREE_SEARCH_OPTIONS,
                          block_private_network=source != "searxng")
    # Wait for this source only. The caller decides whether to try a backup.
    response = await web.search(query, source=source, limit=20,
                                engine_config=engine_config, policy=policy)
    return response



async def search_query(query: str) -> dict:   # -> nije obavezno da vrati dict,nego je hint bukvalno
    """Try Google through local SearXNG, using DuckDuckGo only after a failure.""" 
    import frankensurf as fs

    state_dir = Path(__file__).resolve().parents[2] / ".frankensurf-state" #location to directory
    attempts = []
    sources = [("searxng", {"engines": "google"}), ("duckduckgo_html", None)]

    async with fs.Runtime(state_dir=state_dir) as web: #we pass the state location to fs
        for source, engine_config in sources: #source == searxng or duck , engine== google or None
            if source == "duckduckgo_html":
                await asyncio.sleep(2)

            response = await search_source(web, query, source, engine_config)
            attempts.append({
                "source": source,
                "engine_config": engine_config,
                "receipt": response["receipt"], #f.e. status 500
                "upstream_failures": response.get("upstream_failures", []),
            })

            # Empty and partial answers are valid outcomes, so neither triggers a backup.
            if response["receipt"]["status"] != "failed":
                break

    index = make_index(query, response, 20)
    # Keep the first failure visible even if the backup succeeds.
    index["attempts"] = attempts
    return index
