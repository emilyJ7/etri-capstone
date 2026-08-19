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
save_report
list_reports
list_papers
get_report
delete_report
```

- `search_papers`: 키워드/주제로 OpenAlex를 검색한다. 발행 연도 범위, concept(분야) 필터, 정렬
  (관련도순/피인용수순)을 지원한다.
- `save_report`: 리포트 본문(제목, 연구 질문, 근거·출처가 담긴 내용)과 참조 논문 목록을 함께 저장한다.
- `list_reports`: 저장된 리포트 목록을 최신순으로 조회한다.
- `list_papers`: 리포트 전체를 불러오지 않고 저장된 참고 논문만 조회한다(`report_id`로 특정 리포트만
  필터링 가능).
- `get_report`: 저장된 리포트 하나를 참조 논문 목록과 함께 불러온다.
- `delete_report`: 저장된 리포트를 삭제한다(참조 논문 정보도 함께 삭제된다).

OpenAlex API 키가 있다면 실행 환경의 `OPENALEX_API_KEY` 값으로 전달할 수 있다. 기본적인 검색은 API 키 없이도 실행할 수 있다.

## 데이터 저장

리포트와 참조 논문은 저장소 루트의 `reports.db`(SQLite)에 보존되며, 서버를 재시작해도 유지된다.
이 파일은 `.gitignore`에 의해 커밋되지 않는다.

## 프로젝트 스킬

저장소를 내려받아 프로젝트 루트에서 LLM 애플리케이션을 실행하면 `.claude/skills`의 스킬을 사용할 수 있다.

```text
/interview 구현할 기능의 요구사항을 명세로 정리
/code-review 현재 변경에서 수정이 필요한 문제만 검토
```
