from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import server

app = FastAPI(title="OpenAlex 연구 지원 - 리포트 뷰어 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _raise_for_error(result: dict) -> None:
    """Turn a server.py `{"error": ...}` result into the matching HTTPException.

    Relies on the structured `error_code` field rather than pattern-matching the
    (translated, free-text) error message, so a future rewording of server.py's
    error text can't silently flip a 404 into a 500 or vice versa.
    """
    if "error" not in result:
        return
    status_code = 404 if result.get("error_code") == "not_found" else 500
    raise HTTPException(status_code=status_code, detail=result["error"])


@app.get("/api/reports")
def list_reports() -> list[dict]:
    result = server.list_reports()
    _raise_for_error(result)
    return result["reports"]


@app.get("/api/reports/{report_id}")
def get_report(report_id: int) -> dict:
    result = server.get_report(report_id)
    _raise_for_error(result)
    return result


@app.get("/api/papers")
def list_papers(report_id: int | None = None) -> list[dict]:
    result = server.list_papers(report_id)
    _raise_for_error(result)
    return result["papers"]
