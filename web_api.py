from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from server import _db, _row_to_paper

app = FastAPI(title="OpenAlex 연구 지원 - 리포트 뷰어 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/reports")
def list_reports() -> list[dict]:
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
    return [dict(row) for row in rows]


@app.get("/api/reports/{report_id}")
def get_report(report_id: int) -> dict:
    with _db() as conn:
        report_row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if report_row is None:
            raise HTTPException(status_code=404, detail=f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다.")

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


@app.get("/api/papers")
def list_papers(report_id: int | None = None) -> list[dict]:
    with _db() as conn:
        if report_id is not None:
            existing = conn.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
            if existing is None:
                raise HTTPException(
                    status_code=404, detail=f"report_id {report_id}에 해당하는 리포트를 찾을 수 없습니다."
                )
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

    papers: list[dict] = []
    for row in rows:
        paper = _row_to_paper(row)
        paper["id"] = row["id"]
        paper["report_id"] = row["report_id"]
        paper["report_title"] = row["report_title"]
        papers.append(paper)

    return papers
