from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server import MCPServer


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
DEFAULT_RESULT_LIMIT = 5
MAX_RESULT_LIMIT = 10

server = MCPServer(
    name="openalex-paper-search",
    title="OpenAlex 논문 검색",
    description="논문명을 검색해 OpenAlex의 논문 정보를 반환합니다.",
)


def _author_names(authorships: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for authorship in authorships:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(str(name))
    return names


def _search_openalex(title: str, limit: int) -> dict[str, Any]:
    params = {
        "search": title,
        "per_page": limit,
        "select": (
            "id,display_name,publication_year,doi,authorships,primary_location"
        ),
    }
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
            "query": title,
            "error": f"OpenAlex가 HTTP {error.code} 응답을 반환했습니다.",
            "papers": [],
        }
    except URLError as error:
        return {
            "query": title,
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
            }
        )

    return {
        "query": title,
        "count": len(papers),
        "papers": papers,
    }


@server.tool(structured_output=True)
def search_papers_by_title(
    title: str,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> dict[str, Any]:
    """논문명을 검색어로 사용해 OpenAlex에서 관련 논문을 찾는다.

    Args:
        title: 찾고 싶은 논문의 이름 또는 제목에 포함된 검색어.
        limit: 반환할 논문 수. 기본값은 5이며 최대 10이다.
    """

    normalized_title = title.strip()
    if not normalized_title:
        return {
            "query": title,
            "error": "검색할 논문명을 입력해 주세요.",
            "papers": [],
        }

    safe_limit = max(1, min(limit, MAX_RESULT_LIMIT))
    return _search_openalex(normalized_title, safe_limit)


if __name__ == "__main__":
    server.run(transport="stdio")
