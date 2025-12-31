from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class NewsItem:
    """
    Stable public model representing a normalized news item.

    WARNING: Do not change fields lightly. This is the library's contract.
    """
    title: str
    summary: str
    link: str
    source: str
    published_at: datetime
    language: Optional[str] = None
    category: Optional[str] = None
    guid: Optional[str] = None
