from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server import MCPServer


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10
VALID_SORTS = ("relevance", "citations")

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
            "id,display_name,publication_year,doi,authorships,primary_location,cited_by_count"
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
            }
        )

    return {
        "query": query,
        "count": len(papers),
        "papers": papers,
    }


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
    normalized_query = query.strip()
    if not normalized_query:
        return {"query": query, "error": "검색할 키워드를 입력해 주세요.", "papers": []}

    if sort not in VALID_SORTS:
        return {
            "query": query,
            "error": f"sort는 {VALID_SORTS} 중 하나여야 합니다.",
            "papers": [],
        }

    if year_from is not None and year_to is not None and year_from > year_to:
        return {
            "query": query,
            "error": "year_from은 year_to보다 클 수 없습니다.",
            "papers": [],
        }

    safe_limit = max(1, min(limit, MAX_RESULT_LIMIT))
    return _search_openalex(normalized_query, year_from, year_to, concept, safe_limit, sort)


# ---------------------------------------------------------------------------
# SQLite 영속화
# ---------------------------------------------------------------------------


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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


_init_db()


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
            authors, doi, landing_page_url, cited_by_count 필드를 담을 수 있다.
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
                    landing_page_url, cited_by_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    with _db() as conn:
        if report_id is not None:
            existing = conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
            if existing is None:
                return {"error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다."}
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
    with _db() as conn:
        report_row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if report_row is None:
            return {"error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다."}

        paper_rows = conn.execute(
            "SELECT * FROM report_papers WHERE report_id = ? ORDER BY id", (report_id,)
        ).fetchall()

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
    with _db() as conn:
        existing = conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
        if existing is None:
            return {"error": f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다."}
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))

    return {"success": True, "report_id": report_id}


if __name__ == "__main__":
    server.run(transport="stdio")
