from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


_DEFAULT_FEED_TITLE_HINTS = {
    "news", "press", "보도", "속보", "기사",
}
_DEFAULT_CATEGORY_HINTS = {
    "politics", "economy", "society", "world", "it",
}
_DEFAULT_TITLE_EXCLUDES = {"댓글", "공지", "업데이트", "update log"}


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)


def is_news_entry(entry: Dict[str, Any], *,
                   language: Optional[str] = None,
                   categories: Optional[Iterable[str]] = None,
                   include_keywords: Optional[Iterable[str]] = None,
                   exclude_keywords: Optional[Iterable[str]] = None,
                   ) -> bool:
    """
    Heuristic filter determining if a parsed entry is likely a news article.

    This function expects an entry dict produced by `rss_news.parser.parse_entry`.
    """
    title = (entry.get("title") or "").strip()
    summary = (entry.get("summary") or "").strip()
    link = (entry.get("link") or "").strip()
    category = (entry.get("category") or "").strip()
    lang = (entry.get("language") or "").strip().lower() or None
    published_at = entry.get("published_at")

    # 1st layer: structural
    if not published_at:
        return False
    if not link:
        return False

    # 2nd layer: meta-based hints
    # - category contains typical news sections
    if category:
        if _contains_any(category, _DEFAULT_CATEGORY_HINTS):
            pass
        else:
            # If no category hints, still allow; we'll apply content-based tests next
            pass

    # 3rd layer: content-based
    if len(title) < 10:
        return False
    if _contains_any(title, _DEFAULT_TITLE_EXCLUDES):
        return False

    # Optional user filters
    if language and lang and lang != language.lower():
        return False

    if categories:
        user_cats = {c.lower() for c in categories}
        if category and category.lower() not in user_cats:
            # Soft filter: if provided and entry has a category not in list, drop it
            return False

    if include_keywords:
        if not (_contains_any(title, include_keywords) or _contains_any(summary, include_keywords)):
            return False

    if exclude_keywords:
        if _contains_any(title, exclude_keywords) or _contains_any(summary, exclude_keywords):
            return False

    return True
