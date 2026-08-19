# SPEC: OpenAlex 기반 연구 지원 MCP Server

## Context

`etri-capstone` 저장소에는 OpenAlex 논문 제목 검색 참고 구현(`server.py`)이 포함되어 있다. 이 구현은
`search_papers_by_title` 하나의 Tool만 제공하며, 정확한 논문명 검색과 MCP Server 선언·`stdio` 구동 구조를
보여주기 위한 참고용이다. 이 SPEC은 이 참고 구현을 확장하여 연구 질문에서 리포트 저장·조회까지 이어지는
전체 흐름을 지원하는 MCP Server를 정의한다.

## Goal

LLM(호스트)이 MCP Tool을 통해 OpenAlex에서 논문을 찾고, 직접 비교·분석하여 근거 기반 리포트를 작성하고,
그 결과(리포트와 리포트가 참조한 논문 정보)를 SQLite에 영구 보존·재활용할 수 있게 한다.

## Non-goals

- 다중 사용자 구분, 인증/인가
- 웹 UI, HTTP/네트워크 배포 (`stdio` 전송만 지원)
- 논문 비교·분석·리포트 본문 작성 로직 자체를 서버가 수행하는 것 (호스트 LLM의 책임이며, 서버는 데이터
  검색과 영속화만 담당한다)
- 여러 리포트가 논문 레코드를 공유하는 논문 라이브러리 (논문은 리포트에 종속된다)
- 자동 테스트 작성 (사용자가 명시적으로 요청할 때만 별도로 진행)
- 리포트 수정/갱신 기능 (`save_report`는 항상 새 리포트를 생성한다)

## User Flow

1. 사용자가 연구 질문을 입력한다.
2. 호스트 LLM이 `search_papers`로 OpenAlex를 검색한다 (키워드/주제 검색, 선택적 연도·개념 필터).
3. 호스트 LLM이 검색 결과를 바탕으로 연구 목적에 맞게 논문을 비교·분석한다.
4. 호스트 LLM이 근거와 출처(논문 제목, 저자, DOI/링크)가 포함된 리포트 본문(마크다운)을 작성한다.
5. 호스트 LLM이 `save_report`를 호출해 리포트 본문과 참조한 논문 정보를 함께 저장한다.
6. 사용자는 이후 `list_reports`로 저장된 리포트 목록을 보고, `get_report`로 특정 리포트를 불러오거나,
   `delete_report`로 삭제할 수 있다.

## Functional Requirements

- OpenAlex Works API를 이용한 자유 키워드/주제 검색 (연도 범위, 개념(concept) 필터, 정렬 옵션 지원)
- 검색 결과는 호스트 LLM이 분석·비교할 수 있도록 구조화된 형태로 반환
- 리포트 저장 시 리포트 본문과 참조 논문 목록을 한 번에 저장
- 저장된 리포트의 목록 조회, 개별 불러오기(참조 논문 포함), 삭제 지원
- 모든 데이터는 SQLite에 보존되어 서버 재시작 후에도 유지

## Tool Contracts

| Tool | 입력 | 출력 |
|---|---|---|
| `search_papers` | `query` (str), `year_from?` (int), `year_to?` (int), `concept?` (str), `limit?` (int, 기본 5, 최대 10), `sort?` ("relevance" \| "citations", 기본 relevance) | 논문 목록: `openalex_id, title, publication_year, authors, doi, landing_page_url, cited_by_count, abstract` |
| `save_report` | `title` (str), `research_question` (str), `content` (str, markdown), `papers` (list of `{openalex_id, title, publication_year, authors, doi, landing_page_url, cited_by_count, abstract}`) | `report_id` |
| `list_reports` | (없음) | 리포트 목록: `id, title, research_question, created_at, paper_count` |
| `list_papers` | `report_id?` (int) | 참조 논문 목록 (리포트 전체를 불러오지 않고 조회). `report_id`를 생략하면 저장된 모든 리포트의 논문을 반환하며, 각 항목에 자신의 `id`, `report_id`, `report_title`을 포함한다 |
| `get_report` | `report_id` (int) | `id, title, research_question, content, created_at, updated_at, papers[]` |
| `delete_report` | `report_id` (int) | 성공 여부 |

## Persistence Requirements (SQLite)

- `reports`
  - `id` PK
  - `title`
  - `research_question`
  - `content`
  - `created_at`
  - `updated_at`
- `report_papers`
  - `id` PK
  - `report_id` FK → `reports.id`, `ON DELETE CASCADE`
  - `openalex_id`
  - `title`
  - `publication_year`
  - `authors` (JSON 배열 텍스트)
  - `doi`
  - `landing_page_url`
  - `cited_by_count`
  - `abstract` (OpenAlex `abstract_inverted_index`를 복원한 텍스트, 없을 수 있음)

리포트를 삭제하면 연결된 `report_papers` 행도 함께 삭제된다 (CASCADE). 논문은 리포트 간에 공유되지 않는다.

`report_papers.id`는 향후 개별 논문 단위 기능(예: 논문 하나만 조회/삭제/메모 추가)을 얹을 수 있도록
`list_papers` 응답에 그대로 노출한다.

DB 파일은 저장소 루트에 생성하며, `.gitignore`에 이미 `*.db`/`*.sqlite*` 패턴이 제외되어 있어 커밋되지 않는다.

## Error Behavior

- OpenAlex 요청 실패(HTTP/네트워크 오류)는 예외를 던지지 않고 기존 `search_papers_by_title` 패턴처럼
  `{"error": "..."}` 구조로 반환한다.
- 존재하지 않는 `report_id` 참조(`get_report`, `delete_report`) 시에도 예외 대신 구조화된 에러를 반환한다.
- 빈 검색어, 빈 `papers` 목록 등 입력 검증 실패도 동일하게 구조화된 에러로 반환한다.

## Completion Criteria

- `python server.py`로 `stdio` 구동 시 위 5개 Tool이 모두 등록된다.
- 연구 질문 → `search_papers` 검색 → 호스트 LLM 분석·리포트 작성 → `save_report` 저장 → `list_reports` /
  `get_report` / `delete_report` 흐름이 실제로 동작한다.
- 서버를 재시작해도 이전에 저장한 리포트가 `list_reports`/`get_report`로 그대로 조회된다.
- 삭제한 리포트는 이후 `list_reports`/`get_report`에서 나타나지 않는다.

## Constraints

- Python 3.10 이상, 기존 `mcp==2.0.0` 패키지 유지, `.env`의 `OPENALEX_API_KEY`를 `python-dotenv`로 로드
- 기존 코드 스타일(구조화된 출력, 예외 대신 error dict 반환) 유지
- 표준 라이브러리 `sqlite3` 사용 (추가 ORM 의존성 없음)

## Assumptions

- 리포트 본문은 마크다운 텍스트 하나로 충분하며 별도 첨부 파일은 불필요하다.
- `papers` 저장 시 OpenAlex에서 받은 필드를 그대로 저장하면 충분하며, 저장 시점에 별도 재검증(refetch)은
  하지 않는다.

## Open Risks

- OpenAlex `concept` 필터를 정확히 쓰려면 concept ID를 알아야 하는데, 호스트 LLM이 이를 모를 수 있다.
  필요해지면 concept 검색/조회 보조 Tool 추가를 검토한다.
