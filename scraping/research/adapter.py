from pathlib import Path

from .indexes import make_index


# Automatic routing may use only these free sources, without paid tools or browsers.
FREE_SEARCH_OPTIONS = {
    "action_classes": ("READ_PUBLIC",),
    "provider": "http",
    "allow_paid_fallbacks": False,
    "allow_local_browser": False,
    "allow_real_browser": False,
    "search_source_allow": (
        "searxng", "duckduckgo_html", "bing_rss", "bing_news_rss",
        "google_news_rss", "wikipedia", "hacker_news", "stack_exchange",
        "github", "arxiv", "open_library",
    ),
    "search_paid_parallel": False,
    "search_date_reads": 0,
    "provider_max_attempts_per_candidate": 1,
    "completeness_escalation": False,
    "use_egress_pool": False,
    "rescue_not_found": False,
    "sign_requests": False,
}


async def search_source(web, query: str, source: str | None, engine_config: dict | None) -> dict:
    """Return the search answer; None lets Frankensurf choose the sources."""
    import frankensurf as fs

    # Automatic routing needs access to the fixed local SearXNG service too.
    # Article reads must use a separate policy with private-network blocking enabled.
    policy = fs.WebPolicy(**FREE_SEARCH_OPTIONS,
                          block_private_network=source not in (None, "searxng"))
    # Without an explicit source, Frankensurf manages fallback between allowed sources.
    response = await web.search(query, source=source, limit=20,
                                engine_config=engine_config, policy=policy)
    return response



async def search_query(query: str) -> dict:   # -> nije obavezno da vrati dict,nego je hint bukvalno
    """Run automatic free search and prepare its results for the application."""
    import frankensurf as fs

    # Keep internal state on the Linux filesystem under the current user's home.
    state_dir = Path.home() / ".local" / "share" / "medbrief" / "frankensurf"
    async with fs.Runtime(state_dir=state_dir) as web: #we pass the state location to fs
        # No source or engine restriction: let the library route within our free allowlist.
        response = await search_source(web, query, None, None)
        print("Search source:", response.get("source"))
        print("Search receipt:", response.get("receipt"))

    index = make_index(query, response, 20)
    # The library records its own source attempts, including unsuccessful ones.
    index["attempts"] = response["receipt"].get("search_attempts", [])
    return index
