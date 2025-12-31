"""
rss_news

A lightweight, focused library that fetches RSS/Atom feeds and returns only normalized news items.

Core ideas:
- Input: RSS/Atom feed URLs
- Process: fetch → parse → classify (news-only) → normalize → deduplicate → sort (newest first)
- Output: List[NewsItem]

Example
-------
from rss_news import NewsFetcher

fetcher = NewsFetcher(
    language="ko",
    categories=["IT", "world"],
    include_keywords=None,
    exclude_keywords=["공지", "업데이트"],
)

news = fetcher.fetch([
    "https://www.yna.co.kr/rss/news.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
])

for item in news:
    print(item.published_at, item.source, item.title)
"""
from .models import NewsItem
from .core import NewsFetcher
from .summarizers import SummarizeOptions

__all__ = [
    "NewsItem",
    "NewsFetcher",
    "SummarizeOptions",
]
