from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv()

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_ATOM_NS = "{http://www.w3.org/2005/Atom}"
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SERPAPI_SEARCH_URL = "https://serpapi.com/search"
GOOGLE_SCHOLAR_SOURCE_KEY = "google_scholar"
GOOGLE_SCHOLAR_MONTHLY_LIMIT = int(os.getenv("SERPAPI_MONTHLY_LIMIT", "250"))
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")
DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10
VALID_SORTS = ("relevance", "citations")
VALID_DATE_SORTS = ("relevance", "date")

DB_PATH = Path(__file__).resolve().parent / "reports.db"

server = MCPServer(
    name="openalex-research-assistant",
    title="OpenAlex 연구 지원",
    description=(
        "OpenAlex에서 논문을 검색하고, 호스트 LLM이 작성한 리포트와 참조 논문을"
        " SQLite에 저장·조회·삭제합니다."
    ),
)


# ---------------------------------------------------------------------------
# OpenAlex 검색
# ---------------------------------------------------------------------------


def _author_names(authorships: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for authorship in authorships:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(str(name))
    return names


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, indices in inverted_index.items():
        for index in indices:
            positions[index] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in range(max(positions) + 1) if i in positions)


def _build_filter(year_from: int | None, year_to: int | None, concept: str | None) -> str | None:
    clauses: list[str] = []
    if year_from is not None and year_to is not None:
        clauses.append(f"publication_year:{year_from}-{year_to}")
    elif year_from is not None:
        clauses.append(f"publication_year:>{year_from - 1}")
    elif year_to is not None:
        clauses.append(f"publication_year:<{year_to + 1}")
    if concept:
        clauses.append(f"concepts.id:{concept}")
    return ",".join(clauses) if clauses else None


def _search_openalex(
    query: str,
    year_from: int | None,
    year_to: int | None,
    concept: str | None,
    limit: int,
    sort: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "search": query,
        "per_page": limit,
        "select": (
            "id,display_name,publication_year,doi,authorships,primary_location,"
            "cited_by_count,abstract_inverted_index"
        ),
    }

    filter_str = _build_filter(year_from, year_to, concept)
    if filter_str:
        params["filter"] = filter_str
    if sort == "citations":
        params["sort"] = "cited_by_count:desc"

    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    request = Request(
        f"{OPENALEX_WORKS_URL}?{urlencode(params)}",
        headers={"User-Agent": "etri-capstone/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        return {
            "query": query,
            "error": f"OpenAlex가 HTTP {error.code} 응답을 반환했습니다.",
            "papers": [],
        }
    except URLError as error:
        return {
            "query": query,
            "error": f"OpenAlex에 연결하지 못했습니다: {error.reason}",
            "papers": [],
        }

    papers: list[dict[str, Any]] = []
    for work in payload.get("results", []):
        primary_location = work.get("primary_location") or {}
        papers.append(
            {
                "openalex_id": work.get("id"),
                "title": work.get("display_name"),
                "publication_year": work.get("publication_year"),
                "authors": _author_names(work.get("authorships") or []),
                "doi": work.get("doi"),
                "landing_page_url": primary_location.get("landing_page_url"),
                "cited_by_count": work.get("cited_by_count"),
                "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
                "source": "openalex",
            }
        )

    return {
        "query": query,
        "count": len(papers),
        "papers": papers,
    }


def _validate_search_args(
    query: str,
    sort: str,
    valid_sorts: tuple[str, ...],
    year_from: int | None = None,
    year_to: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Shared input validation for the four search_* tools.

    Returns (error_dict, normalized_query). error_dict is None when the input is
    valid; callers should return it as-is otherwise.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return {"query": query, "error": "검색할 키워드를 입력해 주세요.", "papers": []}, normalized_query

    if sort not in valid_sorts:
        return (
            {"query": query, "error": f"sort는 {valid_sorts} 중 하나여야 합니다.", "papers": []},
            normalized_query,
        )

    if year_from is not None and year_to is not None and year_from > year_to:
        return (
            {"query": query, "error": "year_from은 year_to보다 클 수 없습니다.", "papers": []},
            normalized_query,
        )

    return None, normalized_query


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_RESULT_LIMIT))


def _normalize_doi(doi: str | None) -> str | None:
    """Turn a bare DOI (e.g. Semantic Scholar's `externalIds.DOI`) into a full,
    directly-linkable https://doi.org/... URL. Already-full URLs pass through
    unchanged, so this is safe to apply to any source's `doi` field."""
    if not doi:
        return None
    if doi.startswith("http://") or doi.startswith("https://"):
        return doi
    return f"https://doi.org/{doi}"


@server.tool(structured_output=True)
def search_papers(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    concept: str | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
    sort: str = "relevance",
) -> dict[str, Any]:
    """연구 질문에서 뽑은 키워드나 주제로 OpenAlex에서 관련 논문을 찾는다.

    Args:
        query: 검색할 키워드 또는 주제어. 정확한 논문 제목이 아니어도 된다.
        year_from: 발행 연도 하한(포함). 지정하지 않으면 제한 없음.
        year_to: 발행 연도 상한(포함). 지정하지 않으면 제한 없음.
        concept: 분야를 제한할 OpenAlex concept ID(예: "C41008148").
        limit: 반환할 논문 수. 기본값 5, 최대 10.
        sort: "relevance"(기본, 검색어 관련도순) 또는 "citations"(피인용수순).
    """
    error, normalized_query = _validate_search_args(query, sort, VALID_SORTS, year_from, year_to)
    if error:
        return error

    safe_limit = _clamp_limit(limit)
    return _search_openalex(normalized_query, year_from, year_to, concept, safe_limit, sort)


def _parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    def text(tag: str) -> str | None:
        el = entry.find(f"{ARXIV_ATOM_NS}{tag}")
        if el is None or not el.text:
            return None
        return " ".join(el.text.split())

    arxiv_id = text("id")
    published = text("published")
    year = int(published[:4]) if published else None

    authors: list[str] = []
    for author in entry.findall(f"{ARXIV_ATOM_NS}author"):
        name_el = author.find(f"{ARXIV_ATOM_NS}name")
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    landing_page_url = arxiv_id
    for link in entry.findall(f"{ARXIV_ATOM_NS}link"):
        if link.get("rel") == "alternate":
            landing_page_url = link.get("href") or landing_page_url

    return {
        "openalex_id": arxiv_id,
        "title": text("title"),
        "publication_year": year,
        "authors": authors,
        "doi": None,
        "landing_page_url": landing_page_url,
        "cited_by_count": None,
        "abstract": text("summary"),
        "source": "arxiv",
    }


def _search_arxiv(query: str, limit: int, sort: str, category: str | None) -> dict[str, Any]:
    search_terms = f"all:{query}"
    if category:
        search_terms = f"cat:{category} AND {search_terms}"

    params = {
        "search_query": search_terms,
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance" if sort == "relevance" else "submittedDate",
        "sortOrder": "descending",
    }
    request = Request(
        f"{ARXIV_API_URL}?{urlencode(params)}",
        headers={"User-Agent": "etri-capstone/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
    except HTTPError as error:
        return {"query": query, "error": f"arXiv가 HTTP {error.code} 응답을 반환했습니다.", "papers": []}
    except URLError as error:
        return {"query": query, "error": f"arXiv에 연결하지 못했습니다: {error.reason}", "papers": []}

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        return {"query": query, "error": f"arXiv 응답을 해석하지 못했습니다: {error}", "papers": []}

    papers = [_parse_arxiv_entry(entry) for entry in root.findall(f"{ARXIV_ATOM_NS}entry")]

    return {"query": query, "count": len(papers), "papers": papers}


@server.tool(structured_output=True)
def search_arxiv(
    query: str,
    limit: int = DEFAULT_RESULT_LIMIT,
    sort: str = "relevance",
    category: str | None = None,
) -> dict[str, Any]:
    """arXiv에서 프리프린트 논문을 검색한다. 결과에 항상 초록을 포함한다.

    Args:
        query: 검색할 키워드 또는 주제어.
        limit: 반환할 논문 수. 기본값 5, 최대 10.
        sort: "relevance"(기본, 관련도순) 또는 "date"(최신 제출일순).
        category: arXiv 분류 코드로 제한(예: "cs.CL", "cs.AI"). 지정하지 않으면 전체 분류에서 검색.
    """
    error, normalized_query = _validate_search_args(query, sort, VALID_DATE_SORTS)
    if error:
        return error

    safe_limit = _clamp_limit(limit)
    return _search_arxiv(normalized_query, safe_limit, sort, category)


def _fetch_json_with_backoff(
    request: Request, max_retries: int = 3, base_delay: float = 1.0
) -> tuple[dict[str, Any] | None, str | None]:
    """GET a JSON response, retrying with exponential backoff on HTTP 429.

    Honors a numeric `Retry-After` header when present. Returns (payload, None) on
    success, or (None, error_message) once retries are exhausted or a non-429 error
    occurs.
    """
    delay = base_delay
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=20) as response:
                return json.load(response), None
        except HTTPError as error:
            if error.code == 429 and attempt < max_retries:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else delay
                time.sleep(wait_seconds)
                delay *= 2
                continue
            return None, f"HTTP {error.code} 응답을 반환했습니다."
        except URLError as error:
            return None, f"연결하지 못했습니다: {error.reason}"
    return None, "재시도 한도를 초과했습니다(HTTP 429)."


def _search_semantic_scholar(
    query: str,
    year_from: int | None,
    year_to: int | None,
    limit: int,
    sort: str,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,abstract,externalIds,citationCount,url",
    }
    if year_from is not None and year_to is not None:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from is not None:
        params["year"] = f"{year_from}-"
    elif year_to is not None:
        params["year"] = f"-{year_to}"

    headers = {"User-Agent": "etri-capstone/1.0"}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    request = Request(f"{SEMANTIC_SCHOLAR_SEARCH_URL}?{urlencode(params)}", headers=headers)

    payload, error_message = _fetch_json_with_backoff(request)
    if error_message:
        return {
            "query": query,
            "error": f"Semantic Scholar가 {error_message}",
            "papers": [],
        }

    papers: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        external_ids = item.get("externalIds") or {}
        papers.append(
            {
                "openalex_id": item.get("paperId"),
                "title": item.get("title"),
                "publication_year": item.get("year"),
                "authors": [a.get("name") for a in (item.get("authors") or []) if a.get("name")],
                "doi": _normalize_doi(external_ids.get("DOI")),
                "landing_page_url": item.get("url"),
                "cited_by_count": item.get("citationCount"),
                "abstract": item.get("abstract"),
                "source": "semantic_scholar",
            }
        )

    if sort == "citations":
        papers.sort(key=lambda paper: paper["cited_by_count"] or 0, reverse=True)

    return {"query": query, "count": len(papers), "papers": papers}


@server.tool(structured_output=True)
def search_semantic_scholar(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
    sort: str = "relevance",
) -> dict[str, Any]:
    """Semantic Scholar에서 논문을 검색한다. 초록과 인용수를 함께 제공한다.

    비인증 요청은 공용 레이트리밋(HTTP 429)에 걸리기 쉬워서, 429 응답을 받으면 지수 백오프로
    최대 3회 재시도한다(`Retry-After` 헤더가 있으면 그 값을 우선 사용).

    Args:
        query: 검색할 키워드 또는 주제어.
        year_from: 발행 연도 하한(포함). 지정하지 않으면 제한 없음.
        year_to: 발행 연도 상한(포함). 지정하지 않으면 제한 없음.
        limit: 반환할 논문 수. 기본값 5, 최대 10.
        sort: "relevance"(기본) 또는 "citations"(피인용수순).
    """
    error, normalized_query = _validate_search_args(query, sort, VALID_SORTS, year_from, year_to)
    if error:
        return error

    safe_limit = _clamp_limit(limit)
    return _search_semantic_scholar(normalized_query, year_from, year_to, safe_limit, sort)


def _parse_scholar_result(item: dict[str, Any]) -> dict[str, Any]:
    publication_info = item.get("publication_info") or {}
    summary = publication_info.get("summary") or ""
    year_match = YEAR_PATTERN.search(summary)
    year = int(year_match.group()) if year_match else None

    authors = [
        author.get("name")
        for author in (publication_info.get("authors") or [])
        if author.get("name")
    ]

    cited_by = ((item.get("inline_links") or {}).get("cited_by") or {}).get("total")

    return {
        "openalex_id": item.get("result_id"),
        "title": item.get("title"),
        "publication_year": year,
        "authors": authors,
        "doi": None,
        "landing_page_url": item.get("link"),
        "cited_by_count": cited_by,
        "abstract": item.get("snippet"),
        "source": "google_scholar",
    }


def _search_google_scholar(
    query: str,
    year_from: int | None,
    year_to: int | None,
    limit: int,
    sort: str,
) -> dict[str, Any]:
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return {
            "query": query,
            "error": "SERPAPI_API_KEY가 설정되지 않았습니다. serpapi.com에서 키를 발급받아 .env에 추가해 주세요.",
            "papers": [],
        }

    period = _current_period()
    with _db() as conn:
        reserved = _try_reserve_monthly_usage(
            conn, GOOGLE_SCHOLAR_SOURCE_KEY, period, GOOGLE_SCHOLAR_MONTHLY_LIMIT
        )
        if reserved is None:
            used = _get_monthly_usage(conn, GOOGLE_SCHOLAR_SOURCE_KEY, period)
            return {
                "query": query,
                "error": (
                    f"이번 달({period}) Google Scholar 검색 한도({GOOGLE_SCHOLAR_MONTHLY_LIMIT}회)를 "
                    f"모두 사용했습니다({used}회 사용). 다음 달까지 기다리거나 SerpApi 유료 플랜으로 "
                    "업그레이드해 주세요."
                ),
                "papers": [],
            }

    def _release_reservation() -> None:
        # The slot was reserved before the request; give it back since the call
        # never produced a usable result, so a failed/erroring call doesn't
        # permanently cost a slot of the monthly quota.
        with _db() as release_conn:
            _release_monthly_usage(release_conn, GOOGLE_SCHOLAR_SOURCE_KEY, period)

    params: dict[str, Any] = {
        "engine": "google_scholar",
        "q": query,
        "num": limit,
        "hl": "en",
        "api_key": api_key,
    }
    if year_from is not None:
        params["as_ylo"] = year_from
    if year_to is not None:
        params["as_yhi"] = year_to
    if sort == "date":
        params["scisbd"] = 1

    request = Request(
        f"{SERPAPI_SEARCH_URL}?{urlencode(params)}",
        headers={"User-Agent": "etri-capstone/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        _release_reservation()
        return {"query": query, "error": f"SerpApi가 HTTP {error.code} 응답을 반환했습니다.", "papers": []}
    except URLError as error:
        _release_reservation()
        return {"query": query, "error": f"SerpApi에 연결하지 못했습니다: {error.reason}", "papers": []}
    except Exception:
        # Any other failure (e.g. a non-JSON/truncated response) still means the
        # call produced nothing usable, so the reservation must be given back too.
        _release_reservation()
        raise

    if payload.get("error"):
        _release_reservation()
        return {"query": query, "error": f"SerpApi 오류: {payload['error']}", "papers": []}

    try:
        papers = [_parse_scholar_result(item) for item in payload.get("organic_results", [])]
    except Exception:
        _release_reservation()
        raise

    return {"query": query, "count": len(papers), "papers": papers}


@server.tool(structured_output=True)
def search_google_scholar(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
    sort: str = "relevance",
) -> dict[str, Any]:
    """SerpApi를 통해 Google Scholar에서 논문을 검색한다.

    Google의 공식 API가 아니라 유료 서드파티 서비스 SerpApi를 거친다. 환경변수
    SERPAPI_API_KEY(.env)가 있어야 동작한다. abstract 필드는 전체 초록이 아니라 검색 결과
    스니펫(2~3줄)이다 — Google Scholar 검색 결과 자체가 전체 초록을 제공하지 않기 때문이다.

    무료 요금제 한도를 넘기지 않도록, 이번 달 호출 횟수를 SQLite에 원자적으로 기록해 두고 월
    SERPAPI_MONTHLY_LIMIT(기본 250)회를 넘으면 SerpApi를 호출하지 않고 바로 에러를 반환한다.
    호출이 예약된 뒤 실제 SerpApi 요청이 실패(HTTP 오류, 연결 실패, SerpApi 자체 오류 응답)하면
    예약을 반환해 실패한 호출이 한도를 갉아먹지 않게 한다.

    Args:
        query: 검색할 키워드 또는 주제어.
        year_from: 발행 연도 하한(포함). 지정하지 않으면 제한 없음.
        year_to: 발행 연도 상한(포함). 지정하지 않으면 제한 없음.
        limit: 반환할 논문 수. 기본값 5, 최대 10.
        sort: "relevance"(기본) 또는 "date"(최신순).
    """
    error, normalized_query = _validate_search_args(query, sort, VALID_DATE_SORTS, year_from, year_to)
    if error:
        return error

    safe_limit = _clamp_limit(limit)
    return _search_google_scholar(normalized_query, year_from, year_to, safe_limit, sort)


# ---------------------------------------------------------------------------
# SQLite 영속화
# ---------------------------------------------------------------------------


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    """Add `column` to `table` if missing, tolerating a concurrent process doing the same.

    `PRAGMA table_info` + `ALTER TABLE` is a check-then-act sequence: if two processes
    (e.g. the MCP server and the web viewer, which both import this module) run it at
    the same time against a pre-migration database, both may see the column missing
    before either commits. SQLite serializes the ALTER TABLE itself, so the loser just
    gets "duplicate column name" once the winner's change is visible — which means the
    column now exists, exactly the state this function is trying to reach — so that
    specific error is swallowed instead of crashing the process.
    """
    existing_columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column in existing_columns:
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
    except sqlite3.OperationalError as error:
        if "duplicate column name" not in str(error):
            raise


def _backfill_openalex_source(conn: sqlite3.Connection) -> None:
    """Fill in `source` for rows saved before the `source` column existed.

    Every paper saved before multi-source search was added could only have come
    from `search_papers` (OpenAlex) — the only search tool that existed then —
    so a `source IS NULL` row can be told apart from a genuinely unlabeled one by
    checking whether its `openalex_id` actually looks like an OpenAlex work URL.
    """
    conn.execute(
        """
        UPDATE report_papers
        SET source = 'openalex'
        WHERE source IS NULL AND openalex_id LIKE 'https://openalex.org/%'
        """
    )


def _init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                research_question TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS report_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                openalex_id TEXT,
                title TEXT,
                publication_year INTEGER,
                authors TEXT,
                doi TEXT,
                landing_page_url TEXT,
                cited_by_count INTEGER
            )
            """
        )

        _ensure_column(conn, "report_papers", "abstract", "TEXT")
        _ensure_column(conn, "report_papers", "source", "TEXT")
        _backfill_openalex_source(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                source TEXT NOT NULL,
                period TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (source, period)
            )
            """
        )


_init_db()


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _get_monthly_usage(conn: sqlite3.Connection, source: str, period: str) -> int:
    row = conn.execute(
        "SELECT count FROM api_usage WHERE source = ? AND period = ?", (source, period)
    ).fetchone()
    return row["count"] if row else 0


def _try_reserve_monthly_usage(
    conn: sqlite3.Connection, source: str, period: str, limit: int
) -> int | None:
    """Atomically increment the usage counter iff it is still under `limit`.

    Combines the "is there room left" check and the increment into one SQL statement
    (via `ON CONFLICT ... WHERE ... RETURNING`) so two concurrent calls can't both read
    the same pre-increment count and both proceed, letting usage exceed `limit`.
    Returns the new count on success, or None if the limit was already reached.
    """
    if limit <= 0:
        # The `WHERE count < ?` guard only applies to the ON CONFLICT UPDATE branch;
        # a period's very first reservation takes the plain INSERT branch instead,
        # which has no limit check at all and would otherwise always succeed.
        return None
    row = conn.execute(
        """
        INSERT INTO api_usage (source, period, count) VALUES (?, ?, 1)
        ON CONFLICT(source, period) DO UPDATE SET count = count + 1
        WHERE api_usage.count < ?
        RETURNING count
        """,
        (source, period, limit),
    ).fetchone()
    return row["count"] if row else None


def _release_monthly_usage(conn: sqlite3.Connection, source: str, period: str) -> None:
    """Give back one reserved slot (used when the reserved call ended up failing)."""
    conn.execute(
        "UPDATE api_usage SET count = MAX(count - 1, 0) WHERE source = ? AND period = ?",
        (source, period),
    )


def _row_to_paper(row: sqlite3.Row) -> dict[str, Any]:
    authors_json = row["authors"]
    return {
        "openalex_id": row["openalex_id"],
        "title": row["title"],
        "publication_year": row["publication_year"],
        "authors": json.loads(authors_json) if authors_json else [],
        "doi": row["doi"],
        "landing_page_url": row["landing_page_url"],
        "cited_by_count": row["cited_by_count"],
        "abstract": row["abstract"],
        "source": row["source"],
    }


@server.tool(structured_output=True)
def save_report(
    title: str,
    research_question: str,
    content: str,
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    """작성한 리포트와 그 리포트가 참조한 논문 목록을 함께 저장한다.

    Args:
        title: 리포트 제목.
        research_question: 이 리포트가 답하는 연구 질문.
        content: 근거와 출처가 포함된 리포트 본문(마크다운 텍스트).
        papers: 참조 논문 목록. 각 항목은 openalex_id, title, publication_year,
            authors, doi, landing_page_url, cited_by_count, abstract, source
            (예: "openalex", "arxiv", "semantic_scholar", "google_scholar") 필드를
            담을 수 있다. source를 생략하면 "unknown"으로 저장된다.
    """
    normalized_title = title.strip()
    normalized_question = research_question.strip()
    normalized_content = content.strip()

    if not normalized_title:
        return {"error": "리포트 제목을 입력해 주세요."}
    if not normalized_question:
        return {"error": "연구 질문을 입력해 주세요."}
    if not normalized_content:
        return {"error": "리포트 본문을 입력해 주세요."}
    if not papers:
        return {"error": "참조 논문을 1개 이상 포함해야 합니다."}

    now = datetime.now(timezone.utc).isoformat()

    try:
        with _db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reports (title, research_question, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (normalized_title, normalized_question, normalized_content, now, now),
            )
            report_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO report_papers (
                    report_id, openalex_id, title, publication_year, authors, doi,
                    landing_page_url, cited_by_count, abstract, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        report_id,
                        paper.get("openalex_id"),
                        paper.get("title"),
                        paper.get("publication_year"),
                        json.dumps(paper.get("authors") or []),
                        paper.get("doi"),
                        paper.get("landing_page_url"),
                        paper.get("cited_by_count"),
                        paper.get("abstract"),
                        # Never store NULL here: a NULL source is indistinguishable
                        # from "not migrated yet" (see _backfill_openalex_source),
                        # so a caller that omits this field gets an explicit
                        # "unknown" label instead of silently reopening that gap
                        # for every future save.
                        paper.get("source") or "unknown",
                    )
                    for paper in papers
                ],
            )
    except sqlite3.Error as error:
        return {"error": f"리포트를 저장하지 못했습니다: {error}"}

    return {"report_id": report_id}


@server.tool(structured_output=True)
def list_reports() -> dict[str, Any]:
    """저장된 리포트 목록을 최신순으로 조회한다."""
    try:
        with _db() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.id, r.title, r.research_question, r.created_at,
                    COUNT(p.id) AS paper_count
                FROM reports r
                LEFT JOIN report_papers p ON p.report_id = r.id
                GROUP BY r.id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
    except sqlite3.Error as error:
        return {"error": f"리포트 목록을 조회하지 못했습니다: {error}"}

    return {
        "reports": [
            {
                "id": row["id"],
                "title": row["title"],
                "research_question": row["research_question"],
                "created_at": row["created_at"],
                "paper_count": row["paper_count"],
            }
            for row in rows
        ]
    }


@server.tool(structured_output=True)
def list_papers(report_id: int | None = None) -> dict[str, Any]:
    """리포트 전체를 불러오지 않고 저장된 참고 논문만 훑어본다.

    Args:
        report_id: 지정하면 해당 리포트가 참조한 논문만 반환한다. 생략하면 저장된
            모든 참고 논문을 리포트 구분과 함께 반환한다.
    """
    try:
        with _db() as conn:
            if report_id is not None:
                existing = conn.execute(
                    "SELECT id FROM reports WHERE id = ?", (report_id,)
                ).fetchone()
                if existing is None:
                    return {
                        "error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다.",
                        "error_code": "not_found",
                    }
                rows = conn.execute(
                    """
                    SELECT p.*, r.title AS report_title
                    FROM report_papers p
                    JOIN reports r ON r.id = p.report_id
                    WHERE p.report_id = ?
                    ORDER BY p.id
                    """,
                    (report_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT p.*, r.title AS report_title
                    FROM report_papers p
                    JOIN reports r ON r.id = p.report_id
                    ORDER BY p.report_id, p.id
                    """
                ).fetchall()
    except sqlite3.Error as error:
        return {"error": f"논문 목록을 조회하지 못했습니다: {error}"}

    papers: list[dict[str, Any]] = []
    for row in rows:
        paper = _row_to_paper(row)
        paper["id"] = row["id"]
        paper["report_id"] = row["report_id"]
        paper["report_title"] = row["report_title"]
        papers.append(paper)

    return {"papers": papers}


@server.tool(structured_output=True)
def get_report(report_id: int) -> dict[str, Any]:
    """저장된 리포트 하나를 참조 논문 목록과 함께 불러온다.

    Args:
        report_id: 불러올 리포트의 id.
    """
    try:
        with _db() as conn:
            report_row = conn.execute(
                "SELECT * FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
            if report_row is None:
                return {
                    "error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다.",
                    "error_code": "not_found",
                }

            paper_rows = conn.execute(
                "SELECT * FROM report_papers WHERE report_id = ? ORDER BY id", (report_id,)
            ).fetchall()
    except sqlite3.Error as error:
        return {"error": f"리포트를 불러오지 못했습니다: {error}"}

    return {
        "id": report_row["id"],
        "title": report_row["title"],
        "research_question": report_row["research_question"],
        "content": report_row["content"],
        "created_at": report_row["created_at"],
        "updated_at": report_row["updated_at"],
        "papers": [_row_to_paper(row) for row in paper_rows],
    }


@server.tool(structured_output=True)
def delete_report(report_id: int) -> dict[str, Any]:
    """저장된 리포트를 삭제한다. 연결된 참조 논문 정보도 함께 삭제된다.

    Args:
        report_id: 삭제할 리포트의 id.
    """
    try:
        with _db() as conn:
            existing = conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
            if existing is None:
                return {
                    "error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다.",
                    "error_code": "not_found",
                }
            conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    except sqlite3.Error as error:
        return {"error": f"리포트를 삭제하지 못했습니다: {error}"}

    return {"success": True, "report_id": report_id}


if __name__ == "__main__":
    server.run(transport="stdio")
