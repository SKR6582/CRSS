from __future__ import annotations

from typing import Any, Dict

from .models import NewsItem


def to_news_item(entry: Dict[str, Any]) -> NewsItem:
    """
    Convert a parsed entry dict into a NewsItem.
    Requires:
    - title (may be non-empty string)
    - link (non-empty)
    - source (string)
    - published_at (datetime)
    Optional:
    - language, category, guid
    """
    title = entry.get("title") or ""
    summary = entry.get("summary") or ""
    link = entry.get("link") or ""
    source = entry.get("source") or "unknown"
    published_at = entry.get("published_at")

    # Basic guards; classifier should already have filtered, but re-check
    if not link or not published_at:
        raise ValueError("Entry lacks required fields for NewsItem: link/published_at")

    language = entry.get("language")
    category = entry.get("category")
    guid = entry.get("guid")

    return NewsItem(
        title=title,
        summary=summary,
        link=link,
        source=source,
        published_at=published_at,
        language=language,
        category=category,
        guid=guid,
    )
