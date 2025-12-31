from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Callable

from .fetcher import fetch_many
from .parser import parse_entry
from .classifier import is_news_entry
from .normalizer import to_news_item
from .dedup import deduplicate
from .models import NewsItem
from .summarizers import SummarizeOptions, summarize_items


@dataclass
class FetchOptions:
    language: Optional[str] = None
    categories: Optional[Sequence[str]] = None
    include_keywords: Optional[Sequence[str]] = None
    exclude_keywords: Optional[Sequence[str]] = None
    limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summarize: bool = False
    summarize_options: Optional[SummarizeOptions] = None


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
        summarize: bool = False,
        summarize_options: Optional[SummarizeOptions] = None,
    ) -> None:
        # If language is provided and summarize_options lacks a language hint, propagate it
        if summarize_options and not summarize_options.language and language:
            summarize_options = SummarizeOptions(
                provider=summarize_options.provider,
                model=summarize_options.model,
                max_input_chars=summarize_options.max_input_chars,
                max_workers=summarize_options.max_workers,
                timeout_sec=summarize_options.timeout_sec,
                strategy=summarize_options.strategy,
                language=language,
            )
        self.options = FetchOptions(
            language=language,
            categories=categories,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            summarize=summarize,
            summarize_options=summarize_options,
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

        # Limit (apply before AI summarization to reduce cost)
        if self.options.limit and self.options.limit > 0:
            items = items[: self.options.limit]

        # Optional AI summarization
        if self.options.summarize:
            opts = self.options.summarize_options or SummarizeOptions()
            items = summarize_items(items, options=opts)

        return items
