from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence

from .fetcher import fetch_many
from .parser import parse_entry
from .classifier import is_news_entry
from .normalizer import to_news_item
from .dedup import deduplicate
from .models import NewsItem


@dataclass
class FetchOptions:
    language: Optional[str] = None
    categories: Optional[Sequence[str]] = None
    include_keywords: Optional[Sequence[str]] = None
    exclude_keywords: Optional[Sequence[str]] = None
    limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class NewsFetcher:
    """
    High-level API: fetch RSS/Atom feeds and return a list of normalized NewsItem.

    Pipeline: fetch → parse → classify (news-only) → normalize → deduplicate → sort (newest first)
    """

    def __init__(
        self,
        *,
        language: Optional[str] = None,
        categories: Optional[Sequence[str]] = None,
        include_keywords: Optional[Sequence[str]] = None,
        exclude_keywords: Optional[Sequence[str]] = None,
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> None:
        self.options = FetchOptions(
            language=language,
            categories=categories,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )

    def fetch(self, urls: Iterable[str]) -> List[NewsItem]:
        entries = fetch_many(urls)

        # Parse to common dicts
        parsed = [parse_entry(e) for e in entries]

        # Filter news-only
        filtered = [
            e for e in parsed
            if is_news_entry(
                e,
                language=self.options.language,
                categories=self.options.categories,
                include_keywords=self.options.include_keywords,
                exclude_keywords=self.options.exclude_keywords,
            )
        ]

        # Date range filtering
        if self.options.start_date or self.options.end_date:
            start = self.options.start_date
            end = self.options.end_date
            tmp = []
            for e in filtered:
                dt = e.get("published_at")
                if not dt:
                    continue
                if start and dt < start:
                    continue
                if end and dt > end:
                    continue
                tmp.append(e)
            filtered = tmp

        # Normalize to model
        items = []
        for e in filtered:
            try:
                items.append(to_news_item(e))
            except Exception:
                # Skip malformed rows
                continue

        # Deduplicate and sort (newest first)
        items = deduplicate(items)
        items.sort(key=lambda x: x.published_at, reverse=True)

        # Limit
        if self.options.limit and self.options.limit > 0:
            items = items[: self.options.limit]

        return items
