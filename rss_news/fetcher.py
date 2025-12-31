from __future__ import annotations

from typing import Any, Dict, Iterable, List

import feedparser

from .exceptions import RSSFetchError


def fetch_feed_entries(url: str) -> List[Dict[str, Any]]:
    """
    Fetch a single feed URL and return its entries.

    Raises RSSFetchError on network/parse issues or when feed is malformed (bozo).
    """
    try:
        feed = feedparser.parse(url)
    except Exception as e:  # pragma: no cover - surface as domain error
        raise RSSFetchError(f"Failed to fetch feed: {url} ({e})") from e

    if getattr(feed, "bozo", 0):
        # bozo_exception may exist; include a short message for diagnostics
        exc = getattr(feed, "bozo_exception", None)
        msg = f"Invalid RSS/Atom feed: {url}"
        if exc:
            msg += f" ({exc})"
        raise RSSFetchError(msg)

    entries = getattr(feed, "entries", None)
    if not isinstance(entries, list):
        raise RSSFetchError(f"Feed has no entries: {url}")
    return entries


def fetch_many(urls: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Fetch multiple feeds and aggregate all entries into a single list.

    Failures on individual URLs are isolated and do not abort the whole batch; they
    are ignored to favor best-effort aggregation. If needed, users can fetch one by one
    to receive exceptions.
    """
    all_entries: List[Dict[str, Any]] = []
    for u in urls:
        try:
            all_entries.extend(fetch_feed_entries(u))
        except RSSFetchError:
            # Best-effort: skip failed feeds
            continue
    return all_entries
