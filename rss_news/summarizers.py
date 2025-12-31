from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Iterable, Callable, List
import os
import concurrent.futures as _fut


class Summarizer(Protocol):
    def summarize(self, *, title: str, summary: str, link: str, language: Optional[str] = None) -> str:  # pragma: no cover - interface
        ...


@dataclass
class SummarizeOptions:
    provider: str = "openai"  # "openai" | "gemini"
    model: Optional[str] = None
    max_input_chars: int = 4000
    max_workers: int = 4
    timeout_sec: float = 15.0
    strategy: str = "replace"  # "replace" | "append"
    language: Optional[str] = None  # hint for prompt


class NullSummarizer:
    def summarize(self, *, title: str, summary: str, link: str, language: Optional[str] = None) -> str:
        return summary


class OpenAISummarizer:
    def __init__(self, *, api_key: Optional[str], model: Optional[str], timeout_sec: float) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover - optional dep
            raise RuntimeError("openai package is required for OpenAI summarization. Install with `pip install openai`. ") from e
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set.")
        self._client = OpenAI(api_key=key)
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._timeout = timeout_sec

    def summarize(self, *, title: str, summary: str, link: str, language: Optional[str] = None) -> str:
        # Build compact prompt
        lang = language or "ko"
        sys = (
            f"You are a concise news summarizer. Return a single short paragraph in {lang} (max ~2 sentences). "
            "No preface, no title, no bullets."
        )
        user = (
            f"Title: {title}\n"
            f"Summary: {summary}\n"
            f"Link: {link}\n\n"
            "Task: Provide a concise news summary (objective, no opinions)."
        )
        try:
            # Using Chat Completions API
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
                timeout=self._timeout,
            )
            content = resp.choices[0].message.content if resp and resp.choices else None
            if not content:
                return summary
            return content.strip()
        except Exception:
            return summary


class GeminiSummarizer:
    def __init__(self, *, api_key: Optional[str], model: Optional[str], timeout_sec: float) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:  # pragma: no cover - optional dep
            raise RuntimeError("google-generativeai package is required for Gemini summarization. Install with `pip install google-generativeai`.") from e
        key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) not set.")
        genai.configure(api_key=key)
        self._model_name = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._timeout = timeout_sec
        self._genai = genai

    def summarize(self, *, title: str, summary: str, link: str, language: Optional[str] = None) -> str:
        lang = language or "ko"
        prompt = (
            f"다음 뉴스를 {lang}로 1~2문장으로 간결하게 요약해줘. 군더더기 없이 핵심만.\n"
            f"제목: {title}\n"
            f"요약(원문에서 발췌): {summary}\n"
            f"링크: {link}"
        )
        try:
            model = self._genai.GenerativeModel(self._model_name)
            resp = model.generate_content(prompt, request_options={"timeout": self._timeout})
            text = getattr(resp, "text", None)
            if not text and hasattr(resp, "candidates") and resp.candidates:
                parts = getattr(resp.candidates[0], "content", None)
                text = getattr(parts, "parts", [{}])[0].get("text") if parts else None
            if not text:
                return summary
            return str(text).strip()
        except Exception:
            return summary


def _truncate(s: str, limit: int) -> str:
    if limit <= 0:
        return s
    if len(s) <= limit:
        return s
    return s[:limit]


def build_summarizer(options: Optional[SummarizeOptions]) -> Summarizer:
    if not options:
        return NullSummarizer()
    provider = (options.provider or "").lower()
    if provider == "openai":
        return OpenAISummarizer(api_key=os.getenv("OPENAI_API_KEY"), model=options.model, timeout_sec=options.timeout_sec)
    if provider in {"gemini", "google", "googleai"}:
        return GeminiSummarizer(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"), model=options.model, timeout_sec=options.timeout_sec)
    # Unknown provider → no-op
    return NullSummarizer()


def summarize_items(
    items: Iterable["NewsItem"],
    *,
    options: SummarizeOptions,
) -> List["NewsItem"]:
    """Summarize items' content using the selected provider.

    Returns a new list of NewsItem where summaries may be replaced/appended according to strategy.
    Failures fall back to original summary.
    """
    from .models import NewsItem  # local import to avoid circular

    summarizer = build_summarizer(options)

    def _one(item: NewsItem) -> NewsItem:
        base = f"{item.title}\n\n{item.summary}"
        text = _truncate(base, options.max_input_chars)
        try:
            s = summarizer.summarize(title=item.title, summary=text, link=item.link, language=options.language)
        except Exception:
            s = item.summary
        if not s:
            s = item.summary
        if options.strategy == "append":
            new_summary = f"{item.summary}\n\n[AI 요약]\n{s}" if item.summary else s
        else:  # replace
            new_summary = s
        return NewsItem(
            title=item.title,
            summary=new_summary,
            link=item.link,
            source=item.source,
            published_at=item.published_at,
            language=item.language,
            category=item.category,
            guid=item.guid,
        )

    max_workers = max(1, int(options.max_workers or 1))
    if max_workers == 1:
        return [_one(it) for it in items]

    with _fut.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_one, it) for it in items]
        out: List[NewsItem] = []
        for fu in futures:
            try:
                out.append(fu.result())
            except Exception:  # pragma: no cover - unexpected worker error
                # Fallback: keep original (best-effort)
                pass
        # Preserve length; if any failed, pad with originals to keep positions
        if len(out) != len(list(items)):
            out = out[:0]  # reset and do serial to be safe
            for it in items:
                out.append(_one(it))
        return out
