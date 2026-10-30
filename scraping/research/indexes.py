from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def canonical_url(url: str) -> str:
    """Normalize an HTTP(S) URL for comparison without changing its query."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Expected an absolute HTTP(S) URL.")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs containing credentials are not supported.")

    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"

    port = parts.port
    if port is not None and (parts.scheme, port) not in (("http", 80), ("https", 443)):
        host = f"{host}:{port}"

    return urlunsplit((parts.scheme, host, parts.path, parts.query, ""))


def normalize_results(raw_results: list[dict], limit: int) -> tuple[list[dict], list[str]]:
    """Return unique, numbered results and explanations for any invalid links."""
    # A job may ask for fewer results, but we never keep more than twenty.
    if type(limit) is not int or limit < 1:
        raise ValueError("The result limit must be a positive integer.")
    limit = min(limit, 20)

    results = []
    seen_urls = set()
    errors = []

    for result in raw_results:
        url = result.get("url") or ""

        # One broken link should not prevent us from keeping the other results.
        if not isinstance(url, str):
            errors.append("Invalid result URL: expected a string.")
            continue
        try:
            comparison_url = canonical_url(url)
        except ValueError as error:
            errors.append(f"Invalid result URL: {error}")
            continue

        # Compare normalized links, but keep the original URL for source tracking.
        if comparison_url in seen_urls:
            continue
        seen_urls.add(comparison_url)

        # Give IDs only to results we keep, so the numbering has no gaps.
        results.append({
            "id": len(results) + 1,
            "title": result.get("title") or url,
            "url": url,
            "snippet": result.get("snippet") or "",
        })
        if len(results) == limit:
            break

    return results, errors


def get_search_status(response: dict, results: list[dict], errors: list[str]) -> tuple[str, str | None]:
    """Return the search status and a combined explanation of its problems."""
    # Keep the provider's explanation so a failed search does not look empty.
    problems = []
    receipt = response.get("receipt") or {}
    failure = receipt.get("failure")
    if failure:
        code = failure.get("code") or "SEARCH_FAILED"
        message = failure.get("message") or "The search provider reported a failure."
        problems.append(f"{code}: {message}")
    elif receipt.get("status") != "observed":
        problems.append("The search provider did not confirm a successful response.")

    if response.get("coverage") == "partial":
        problems.append("The search provider returned partial coverage.")
    if response.get("upstream_failures"):
        problems.append(f"Some search sources failed: {response['upstream_failures']}")

    # Include link problems without changing the list supplied by the caller.
    problems.extend(errors)

    # Keep useful results even when part of the search failed.
    if problems:
        status = "partial" if results else "failed"
    else:
        status = "success" if results else "empty"

    return status, "; ".join(problems) if problems else None


def make_index(query: str, response: dict, limit: int) -> dict:
    """Combine prepared results, search status and source metadata into an index."""
    results, errors = normalize_results(response.get("results") or [], limit)
    status, error = get_search_status(response, results, errors)

    # UTC makes timestamps comparable even when developers use different time zones.
    return {
        "query": query,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "source": response.get("source"),
        "status": status,
        "error": error,
        "results": results,
    }
