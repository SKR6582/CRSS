from __future__ import annotations

from typing import Iterable, List, Set

from .models import NewsItem


def deduplicate(items: Iterable[NewsItem]) -> List[NewsItem]:
    """
    Remove duplicates by priority: guid -> link -> title+source hash.
    Keeps the first occurrence and preserves original order.
    """
    seen: Set[str] = set()
    out: List[NewsItem] = []

    def make_key(it: NewsItem) -> str:
        if it.guid:
            return f"guid::{it.guid}"
        if it.link:
            return f"link::{it.link}"
        return f"ts::{hash((it.title, it.source))}"

    for it in items:
        key = make_key(it)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
