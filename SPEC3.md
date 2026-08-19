# SPEC3: 리포트/논문 웹 뷰어 (읽기 전용)

## Context

지금까지 저장된 리포트와 논문은 MCP Tool(`list_reports`, `get_report`, `list_papers`)을 통해서만
조회할 수 있었다. 브라우저에서 바로 확인하고 싶다는 요청에 따라 읽기 전용 웹 뷰어를 추가한다.

## Goal

`reports.db`에 저장된 리포트와 참고 논문을 브라우저에서 목록/상세로 조회할 수 있게 한다.

## Non-goals

- 채팅/분석 기능 (Claude API 등 LLM 호출 없음 — 별도 API 비용 이슈를 피하기 위해 의도적으로 제외)
- 쓰기 기능 (저장/삭제 등은 웹에서 지원하지 않음, MCP Tool로만 수행)
- 배포/호스팅 (로컬 개발 서버 실행만 다룬다)

## 아키텍처

- **API 서버**: `web_api.py` (FastAPI). `server.py`의 `_db()`, `_row_to_paper()`를 재사용해
  `reports.db`를 직접 읽는다. 3개 GET 엔드포인트만 제공:
  - `GET /api/reports`
  - `GET /api/reports/{report_id}`
  - `GET /api/papers?report_id=` (선택 필터)
- **프론트엔드**: `frontend/` (React + Vite + react-router-dom + react-markdown). 3개 화면:
  - 리포트 목록 (`/`)
  - 리포트 상세 (`/reports/:reportId`) — 본문을 마크다운으로 렌더링, 참조 논문 목록 포함
  - 논문 목록 (`/papers`) — 저장된 모든 논문을 리포트 구분과 함께 표시

## 실행 방법

`README.md`의 "웹 뷰어" 절 참고. API 서버(`:8000`)와 Vite dev 서버(`:5173`)를 각각 띄운다.

## 확인한 내용

- 실제 저장된 리포트(`report_id=1`, "제조 분야 AI/LLM 에이전트 활용 동향 비교")로 3개 화면 모두
  브라우저에서 정상 렌더링 확인 (목록 → 상세 → 마크다운 표 렌더링 → 참조 논문 목록 → 논문 목록)
- 콘솔 에러 없음

## Constraints / 알아둘 점

- FastAPI를 처음 설치할 때 `mcp` 패키지가 요구하는 `starlette`/`uvicorn` 버전과 충돌해 자동으로
  다운그레이드되었다. `fastapi==0.141.1` + `starlette==1.6.0`(기존 유지) + `uvicorn==0.52.3`(기존
  유지) 조합으로 고정해서 해결했다. 향후 의존성을 건드릴 때 이 조합이 깨지지 않는지 확인이 필요하다.
- Node.js가 로컬에 없어 `winget install OpenJS.NodeJS.LTS`로 새로 설치했다.

## Open Risks

- 리포트/논문 수가 많아지면 목록 페이지에 페이지네이션이 필요할 수 있다 (현재는 전체를 한 번에 반환).
