from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import time
import feedparser


def _to_datetime(entry: Dict[str, Any]) -> Optional[datetime]:
    """
    Convert feed entry date fields to timezone-aware UTC datetime.
    Priority: published_parsed -> updated_parsed -> created_parsed -> None.
    """
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        val = entry.get(key)
        if isinstance(val, time.struct_time):
            try:
                ts = time.mktime(val)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                continue
    # Fallback: try string timestamps with feedparser's *_parsed missing.
    for key in ("published", "updated", "created"):
        s = entry.get(key)
        if isinstance(s, str) and s:
            try:
                # time.strptime with RFC822-like formats is brittle; rely on feedparser to fill *_parsed normally
                # Here we do a minimal attempt, otherwise return None.
                parsed = feedparser._parse_date(s)  # type: ignore[attr-defined]
                if isinstance(parsed, time.struct_time):
                    ts = time.mktime(parsed)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                continue
    return None


def _get_source(entry: Dict[str, Any]) -> str:
    # Try feed title embedded on entry, else hostname from link
    src = entry.get("source", {}) or {}
    if isinstance(src, dict):
        title = src.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    for key in ("feedburner_origlink", "link"):
        link = entry.get(key)
        if isinstance(link, str) and link:
            # crude host extraction
            try:
                from urllib.parse import urlparse

                host = urlparse(link).netloc
                if host:
                    return host
            except Exception:
                pass
    # Final fallback
    return "unknown"


def _get_language(entry: Dict[str, Any]) -> Optional[str]:
    lang = entry.get("language") or entry.get("dc_language") or entry.get("lang")
    if isinstance(lang, str):
        return lang.lower()
    return None


def parse_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a raw feed entry (from feedparser) to a normalized dict with common fields.
    Fields: title, summary, link, source, published_at (datetime|None), language, category, guid
    """
    title = (entry.get("title") or "").strip()
    summary = (entry.get("summary") or entry.get("description") or "").strip()
    link = (entry.get("link") or entry.get("feedburner_origlink") or "").strip()

    # Prefer entry id/guid if present
    guid = None
    for k in ("id", "guid"):
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            guid = v.strip()
            break

    # Category: prefer first tag term
    category = None
    tags = entry.get("tags")
    if isinstance(tags, list) and tags:
        t0 = tags[0]
        if isinstance(t0, dict):
            term = t0.get("term")
            if isinstance(term, str) and term.strip():
                category = term.strip()

    published_at = _to_datetime(entry)
    source = _get_source(entry)
    language = _get_language(entry)

    return {
        "title": title,
        "summary": summary,
        "link": link,
        "source": source,
        "published_at": published_at,
        "language": language,
        "category": category,
        "guid": guid,
    }
