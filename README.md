# OpenAlex 기반 연구 지원 MCP Server

## 프로젝트 목표

OpenAlex를 활용하여 자신의 연구 분야에 특화된 MCP Server를 설계하고 구현한다.

구현한 MCP Server는 LLM이 제공 기능을 식별하고 연결하여 필요한 Tool을 호출할 수 있어야 한다. 논문 검색에서 시작하여 데이터 비교와 리포트 작성으로 이어지는 연구 과정에 실질적으로 도움이 되는 기능을 제공하는 것이 목표다.

예를 들어 인터넷 기술 연구원은 네트워크·통신 분야의 논문 탐색과 기술 비교에 적합한 기능을 만들 수 있다. 환경공학 연구원은 환경 지표, 실험 조건, 측정 결과를 중심으로 논문을 검색하고 비교하는 기능을 설계할 수 있다.

완성된 결과물은 다음 흐름을 지원해야 한다.

```text
연구 질문
→ OpenAlex를 활용한 논문 검색
→ 연구 목적에 따른 데이터 비교
→ 근거와 출처가 포함된 리포트 작성
```

## 참고 구현

이 저장소에는 Python으로 실행하는 가장 기본적인 MCP Server가 포함되어 있다.

참고 Tool은 입력받은 논문명을 OpenAlex에서 검색하고, 검색된 논문의 제목·발행 연도·저자·DOI·OpenAlex 주소를 반환한다. 이 코드는 MCP Server의 선언, Tool 등록, OpenAlex 요청과 `stdio` 구동 구조를 확인하기 위한 참고 구현이다.

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
search_papers_by_title
```

입력한 논문명을 OpenAlex에서 검색하고 관련 논문 목록을 반환한다.

OpenAlex API 키가 있다면 실행 환경의 `OPENALEX_API_KEY` 값으로 전달할 수 있다. 기본적인 검색은 API 키 없이도 실행할 수 있다.
