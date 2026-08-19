# OpenAlex 기반 연구 지원 MCP Server

## 실습 목표

MCP Server를 직접 구현하여 LLM이 논문을 찾고 분석·비교하며, 작성한 리포트를 저장하고 다시 활용할 수 있게 한다.

## 요구사항

- OpenAlex를 활용한 논문 검색
- LLM이 식별하고 호출할 수 있는 MCP Tool 제공
- 연구 분야에 맞는 논문 분석 및 비교
- 근거와 출처가 포함된 리포트 작성
- 참고 논문과 리포트 저장, 목록 조회, 불러오기 및 삭제
- SQLite를 사용한 데이터 보존

완성된 결과물은 다음 흐름을 지원해야 한다.

```text
연구 질문
→ OpenAlex를 활용한 논문 검색
→ 연구 목적에 따른 데이터 비교
→ 근거와 출처가 포함된 리포트 작성
→ 리포트 저장
→ 저장된 리포트 목록 조회·불러오기·삭제
```

## 구현

`SPEC.md`에 정리된 요구사항에 따라, OpenAlex 논문 검색부터 리포트 저장·조회·삭제까지 지원하는 MCP
Server가 `server.py`에 구현되어 있다. 논문 비교·분석과 리포트 본문 작성은 Tool을 호출하는 호스트
LLM이 수행하며, 서버는 검색과 SQLite 영속화만 담당한다.

## 준비

Python 3.10 이상이 필요하다.

먼저 Python 버전을 확인한다. 3.10보다 낮다면 설치된 Python 3.10 이상의 실행 명령을 사용한다.

```bash
python3 --version
```

Windows PowerShell:

```powershell
python --version
```

macOS와 Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## API 키 (선택)

기본적인 검색은 API 키 없이도 동작하지만, 요청량이 많거나 크레딧/레이트리밋에 걸리면 키가 필요할 수
있다. 저장소 루트에 `.env` 파일을 만들고 아래처럼 채우면 `server.py`가 시작 시 자동으로 읽는다.

```text
OPENALEX_API_KEY=여기에_키_입력
SEMANTIC_SCHOLAR_API_KEY=여기에_키_입력
SERPAPI_API_KEY=여기에_키_입력
```

arXiv는 API 키가 필요 없다. `SERPAPI_API_KEY`는 `search_google_scholar`에 **필수**다(키가 없으면
에러를 반환한다) — [serpapi.com](https://serpapi.com)에서 가입 후 발급받는다(무료 플랜: 월 250회).
무료 플랜을 실수로 넘겨 과금되지 않도록, 서버가 이번 달 호출 횟수를 자체 기록해 250회(기본값)에
도달하면 SerpApi를 호출하지 않고 차단한다. 유료 플랜으로 올렸다면 `.env`에 `SERPAPI_MONTHLY_LIMIT`를
원하는 값으로 설정해 한도를 조정할 수 있다. `.env`는 `.gitignore`에 등록되어 있어 커밋되지 않는다.

## MCP Server 실행

```bash
python server.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe server.py
```

MCP Host는 위 명령으로 Server를 실행하고 표준 입력과 표준 출력을 통해 통신한다.

## 제공 Tool

```text
search_papers
search_arxiv
search_semantic_scholar
search_google_scholar
save_report
list_reports
list_papers
get_report
delete_report
```

- `search_papers`: 키워드/주제로 OpenAlex를 검색한다. 발행 연도 범위, concept(분야) 필터, 정렬
  (관련도순/피인용수순)을 지원하며, 결과에 초록(abstract, 확보 가능한 경우)을 포함한다.
- `search_arxiv`: arXiv에서 프리프린트를 검색한다. 분류 코드(`category`, 예: `cs.CL`) 필터를
  지원하고, 결과에 항상 초록을 포함한다.
- `search_semantic_scholar`: Semantic Scholar에서 논문을 검색한다. 발행 연도 범위를 지원하고,
  초록과 인용수를 함께 제공한다.
- `search_google_scholar`: SerpApi(유료 서드파티 서비스)를 통해 Google Scholar를 검색한다.
  `SERPAPI_API_KEY`가 필수이며, `abstract` 필드는 전체 초록이 아니라 검색 결과 스니펫이다.
- `save_report`: 리포트 본문(제목, 연구 질문, 근거·출처가 담긴 내용)과 참조 논문 목록을 함께 저장한다.
  참조 논문은 검색 Tool 4개 중 어디서 가져온 것이든 그대로 저장할 수 있다(`source` 필드로 출처 구분).
- `list_reports`: 저장된 리포트 목록을 최신순으로 조회한다.
- `list_papers`: 리포트 전체를 불러오지 않고 저장된 참고 논문만 조회한다(`report_id`로 특정 리포트만
  필터링 가능).
- `get_report`: 저장된 리포트 하나를 참조 논문 목록과 함께 불러온다.
- `delete_report`: 저장된 리포트를 삭제한다(참조 논문 정보도 함께 삭제된다).

Google Scholar는 공식 API가 없고 직접 스크래핑은 이용약관 위반이자 불안정하다. 대신 SerpApi(유료
서드파티 스크래핑 서비스)를 경유하는 `search_google_scholar`로 지원한다.

## 데이터 저장

리포트와 참조 논문은 저장소 루트의 `reports.db`(SQLite)에 보존되며, 서버를 재시작해도 유지된다.
이 파일은 `.gitignore`에 의해 커밋되지 않는다.

## 웹 뷰어 (읽기 전용)

저장된 리포트와 참고 논문을 브라우저에서 확인할 수 있는 읽기 전용 뷰어를 `web_api.py`(FastAPI)와
`frontend/`(React + Vite)에 구현해 두었다. 채팅이나 분석 기능은 없고, `reports.db`에 이미 저장된
내용을 보여주기만 한다 — 따라서 Claude API 등 별도 LLM 비용은 들지 않는다.

API 서버 실행:

```bash
python -m pip install -r requirements.txt
uvicorn web_api:app --port 8000
```

프론트엔드 실행 (Node.js 필요):

```bash
cd frontend
npm install
npm run dev
```

`npm run dev`가 알려주는 주소(기본 http://localhost:5173)로 접속하면 리포트 목록/상세, 논문 목록을
볼 수 있다. API 서버(`:8000`)가 먼저 떠 있어야 한다.

## 프로젝트 스킬

저장소를 내려받아 프로젝트 루트에서 LLM 애플리케이션을 실행하면 `.claude/skills`의 스킬을 사용할 수 있다.

```text
/interview 구현할 기능의 요구사항을 명세로 정리
/code-review 현재 변경에서 수정이 필요한 문제만 검토
```
