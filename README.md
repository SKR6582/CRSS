# rss_news — 뉴스 전용 RSS 수집/정규화 엔진

“RSS를 긁는 도구”가 아니라, RSS/Atom 피드에서 뉴스만 선별해 표준 `NewsItem` 모델로 정규화하는 엔진입니다.

- 입력: 하나 이상의 RSS/Atom URL
- 처리: fetch → parse → classify(뉴스 전용) → normalize → deduplicate → sort(최신순)
- 출력: 일관된 `NewsItem` 리스트

이 패키지는 다양한 언론사/플랫폼의 RSS 구조 차이를 흡수하고, 뉴스가 아닌 항목(공지, 업데이트 로그 등)을 최대한 배제합니다.


## 주요 특징
- 뉴스 전용 필터: 구조/메타/내용 기준으로 일관된 판별
- 표준 모델: 안정적인 `NewsItem` 데이터클래스 계약(API)
- 중복 제거: `guid → link → title+source` 우선순위
- 시간 정규화: 가능한 한 UTC 타임존 인식 `datetime`으로 통일
- 최신순 정렬 및 Top-N 제한
- 언어/카테고리/키워드 및 날짜 범위 필터 옵션


## 설치

프로젝트에 필요한 의존성을 설치하려면 `requirements.txt` 파일을 사용하세요.

```bash
pip install -r requirements.txt
```

이 패키지는 로컬 모듈 구조입니다. 프로젝트에 `rss_news` 디렉터리를 포함하여 사용하거나, 나중에 PyPI 패키지로 배포하여 `pip install`로 설치할 수 있습니다.

- **요구 사항**: Python 3.9+
- **의존성**: `requirements.txt` 참조


## 빠른 시작
```python
from rss_news import NewsFetcher

fetcher = NewsFetcher(
    language="ko",
    categories=["IT", "world"],
    exclude_keywords=["공지", "업데이트"],
    limit=100,
)

news = fetcher.fetch([
    "https://www.yna.co.kr/rss/news.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
])

for item in news:
    print(item.published_at, item.source, item.title)
```


## Public API
### NewsItem (stable)
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NewsItem:
    title: str
    summary: str
    link: str
    source: str
    published_at: datetime
    language: str | None = None
    category: str | None = None
    guid: str | None = None
```
이 모델은 라이브러리의 핵심 계약으로, 자주 변경하지 않습니다.

### NewsFetcher
```python
from rss_news import NewsFetcher
from datetime import datetime
from typing import Iterable, Sequence

# __init__ signature (for reference)
# NewsFetcher(
#     *,
#     language: str | None = None,
#     categories: Sequence[str] | None = None,
#     include_keywords: Sequence[str] | None = None,
#     exclude_keywords: Sequence[str] | None = None,
#     limit: int | None = None,
#     start_date: datetime | None = None,
#     end_date: datetime | None = None,
#     summarize: bool = False,
#     summarize_options: SummarizeOptions | None = None,
# )

# Usage
fetcher = NewsFetcher()
urls: Iterable[str] = ["https://example.com/rss.xml"]
items: list[NewsItem] = fetcher.fetch(urls)
```

- `language`: 언어 코드(예: `"ko"`, `"en"`)로 필터
- `categories`: 카테고리 힌트로 필터(존재 시 포함 매칭)
- `include_keywords`: 제목/요약에 키워드가 하나 이상 포함되어야 통과
- `exclude_keywords`: 제목/요약에 포함되면 제외
- `limit`: 최종 결과 상위 N개로 제한(최신순)
- `start_date`, `end_date`: 발행일 기준 범위 필터(경계 포함)

반환값은 최신순으로 정렬된 `NewsItem` 리스트입니다.


## 동작 원리(파이프라인)
1) Fetch: `feedparser`로 URL별 피드를 가져옵니다. 
2) Parse: 항목을 공통 dict로 매핑합니다(`title`, `summary`, `link`, `source`, `published_at`, `language`, `category`, `guid`). 가능한 한 `published_at`을 타임존 인식 UTC로 변환합니다.
3) Classify(뉴스 전용): 다음 기준으로 뉴스만 통과시킵니다.
   - 구조: 날짜/링크 필드 존재
   - 내용: 제목 길이 ≥ 10, 제목에 비뉴스 용어(예: "공지", "댓글", "업데이트") 포함 시 제외
   - 메타: 카테고리/피드 타이틀 등 힌트를 활용(엄격 필터는 아님)
   - 사용자 옵션: 언어, 카테고리, 키워드 포함/제외 필터 적용
4) Normalize: `NewsItem` 데이터클래스로 변환
5) Deduplicate: `guid → link → (title+source 해시)` 우선순위로 중복 제거(첫 등장 보존)
6) Sort: `published_at` 기준 내림차순(최신순)
7) Limit: 지정 시 상위 N개로 제한


## 예제 모음
- 언어/카테고리 필터:
```python
fetcher = NewsFetcher(language="en", categories=["Technology", "World"]) 
items = fetcher.fetch(["https://feeds.bbci.co.uk/news/rss.xml"]) 
```

- 키워드 포함/제외:
```python
fetcher = NewsFetcher(include_keywords=["AI", "robot"], exclude_keywords=["opinion", "공지"]) 
items = fetcher.fetch(["https://www.theverge.com/rss/index.xml"]) 
```

- 날짜 범위 + Top N:
```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
fetcher = NewsFetcher(start_date=now - timedelta(days=1), end_date=now, limit=50)
items = fetcher.fetch(["https://feeds.bbci.co.uk/news/rss.xml"]) 
```


## 시간/타임존 처리
- `parser`는 `published_parsed/updated_parsed/created_parsed` 등에서 가능한 값을 찾아 UTC `datetime`으로 변환하려 시도합니다.
- 문자열 날짜만 있는 경우도 `feedparser`의 파서를 활용해 최대한 UTC로 변환합니다.
- 날짜를 얻을 수 없으면 해당 항목은 뉴스 판별에서 제외되거나 후속 단계에서 걸러질 수 있습니다.


## 중복 제거 전략
- 우선순위: `guid` → `link` → `hash(title, source)`
- 첫 번째로 등장한 항목을 보존합니다.


## 에러 처리
- 단일 URL에서 `feedparser` 보조(bozo) 플래그로 잘못된 피드를 감지하면 예외가 발생할 수 있습니다.
- 복수 URL 수집 시에는 URL 단위로 실패를 무시하고 가능한 결과를 최대한 수집하는 "best-effort" 전략을 따릅니다.
- 파싱/정규화 중 비정상 항목은 개별적으로 건너뜁니다.


## 베스트 프랙티스
- 가능한 HTTPS 피드를 사용하세요.
- 언론사별 RSS 구조가 상이할 수 있으므로, 필요한 경우 `include_keywords`/`exclude_keywords`로 보정하세요.
- 다국어 피드는 `language` 옵션으로 좁히는 것이 정확도에 유리합니다.


## 샘플 피드
- 연합뉴스: `https://www.yna.co.kr/rss/news.xml`
- BBC News: `https://feeds.bbci.co.uk/news/rss.xml`
- The Verge: `https://www.theverge.com/rss/index.xml`

서비스 약관(ToS)과 robots 정책을 존중하세요.


## 프로젝트 구조
```
rss_news/
 ├─ __init__.py       # Public API exports: NewsFetcher, NewsItem
 ├─ core.py           # Orchestrates the pipeline (NewsFetcher)
 ├─ fetcher.py        # Feed fetching via feedparser (bozo check)
 ├─ parser.py         # Entry parsing and date normalization (UTC)
 ├─ classifier.py     # News-only heuristics + optional filters
 ├─ normalizer.py     # Convert dict → NewsItem model
 ├─ dedup.py          # Dedup by guid → link → title+source
 ├─ models.py         # NewsItem dataclass (stable API)
 └─ exceptions.py     # Domain exceptions
```


## AI 요약 (옵션 기능)
이제 수집된 뉴스 항목에 대해 AI 요약을 적용할 수 있습니다. OpenAI 또는 Google Gemini 중에서 선택할 수 있으며, 기본적으로는 비활성화되어 기존 동작에 영향이 없습니다.

### 설치 (선택적 의존성)
- OpenAI 사용 시: `pip install openai`
- Gemini 사용 시: `pip install google-generativeai`

### 환경 변수
- OpenAI
  - `OPENAI_API_KEY`: 필수
  - `OPENAI_MODEL`: 선택(기본값 `gpt-4o-mini`)
- Gemini
  - `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`: 필수(둘 중 하나)
  - `GEMINI_MODEL`: 선택(기본값 `gemini-1.5-flash`)

### 사용 예시
```python
from rss_news import NewsFetcher, SummarizeOptions

# OpenAI로 요약
fetcher = NewsFetcher(
    summarize=True,
    summarize_options=SummarizeOptions(
        provider="openai",        # 또는 "gemini"
        model=None,                # 환경변수 기본값 사용
        strategy="replace",       # "replace" | "append"
        max_input_chars=4000,
        max_workers=4,             # 동시 요약(요금/레이트리밋 고려)
        timeout_sec=15.0,
        language="ko",            # 요약 언어 힌트(미설정 시 language 옵션 전파)
    ),
)
items = fetcher.fetch([
    "https://www.yna.co.kr/rss/news.xml",
])
```

```python
from rss_news import NewsFetcher, SummarizeOptions

# Gemini로 요약 + 기존 요약에 덧붙이기
fetcher = NewsFetcher(
    summarize=True,
    summarize_options=SummarizeOptions(
        provider="gemini",
        strategy="append",
        max_workers=1,  # 레이트리밋 우려 시 직렬 처리
        language="ko",
    ),
)
items = fetcher.fetch(["https://feeds.bbci.co.uk/news/rss.xml"]) 
for it in items[:3]:
    print(it.title)
    print(it.summary)  # [AI 요약] 블록이 포함되거나, 대체된 요약
```

### 동작 방식
- 파이프라인 마지막 단계에서(정렬/Top-N 제한 이후) 항목의 `title`과 기존 `summary`를 입력으로 요약을 수행합니다.
- 오류/타임아웃/키 누락 시 원래 요약으로 안전하게 폴백합니다.
- `strategy="replace"`는 AI가 생성한 요약으로 대체, `append`는 기존 요약 아래에 `[AI 요약]` 블록으로 덧붙입니다.

### 비용/안전
- 요청당 비용이 발생할 수 있습니다. `limit`을 활용해 상위 N개에만 요약을 적용하세요.
- 민감정보를 포함한 원문을 외부 API로 전송하지 않도록 주의하세요.

## 로드맵 / 확장 포인트
- on-item 훅(예: AI 요약) 추가 → 기본 제공 완료
- 감정 분석 파이프라인
- 속보 감지(발행 간격 기반)


## 라이선스
이 프로젝트는 저장소의 `LICENSE` 파일을 따릅니다.


## Discord 봇 예제

이 저장소에는 `rss_news` 라이브러리를 사용하여 최신 뉴스를 Discord 채널에 게시하는 간단한 Discord 봇 예제(`discord_bot.py`)가 포함되어 있습니다.

### 설치

봇을 실행하는 데 필요한 모든 라이브러리를 설치하려면 프로젝트 루트 디렉토리에서 다음 명령을 실행하십시오.

```bash
pip install -r requirements.txt
```

### 설정
1.  프로젝트 루트 디렉토리에 `.env`라는 이름의 파일을 생성합니다.
2.  `.env` 파일에 Discord 봇 토큰을 다음 형식으로 추가합니다. `YOUR_BOT_TOKEN`을 실제 봇 토큰으로 교체하세요.

    ```
    DISCORD_BOT_MPSB="YOUR_BOT_TOKEN"
    ```

### 실행
봇을 시작하려면 다음 명령어를 실행하세요.

```bash
python discord_bot.py
```

봇이 성공적으로 로그인하면, Discord 채널에서 `!news` 명령어를 입력하여 최신 뉴스를 받아볼 수 있습니다.
