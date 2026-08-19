# etri-capstone 실행 가이드

이 문서는 이 프로젝트를 처음 받아서 내 컴퓨터에서 실제로 돌려보는 방법을 순서대로 설명합니다.
컴퓨터를 잘 몰라도 따라 할 수 있도록, 한 줄씩 무엇을 왜 하는지 적어두었습니다.

> Claude Code에서 바로 열어보는 공유 링크: https://claude.ai/claude-code/onboard/D4XohL_yKESV

## 이 프로그램은 뭐 하는 프로그램인가요?

한 문장으로: **논문을 찾아주고, 비교해서 리포트를 써주고, 그 리포트를 웹사이트에서 보여주는 프로그램**입니다.

두 부분으로 이루어져 있습니다.

1. **서버(server.py)**: Claude 같은 AI가 논문을 검색하고, 리포트를 저장하도록 도와주는 부분.
   AI가 이 서버의 기능(Tool이라고 부름)을 호출해서 씁니다.
2. **웹사이트(web_api.py + frontend 폴더)**: 저장된 리포트와 논문을 브라우저에서 눈으로 볼 수 있게
   보여주는 부분.

처음 내 컴퓨터에 받아오면 저장된 리포트가 하나도 없는 게 정상입니다(데이터가 없을 뿐, 고장난 게
아닙니다). AI와 연결해서 검색·저장을 해봐야 웹사이트에 내용이 채워집니다.

## 시작하기 전에: 준비물 체크리스트

아래 4가지 프로그램이 내 컴퓨터에 설치되어 있어야 합니다. 없으면 설치 방법도 같이 적어두었습니다.

- [ ] **Git** — 코드를 다운받는 프로그램
- [ ] **Python 3.10 이상** — 서버를 실행하는 프로그램
- [ ] **Node.js** — 웹사이트 화면을 만드는 프로그램
- [ ] **GitHub 계정** — 코드를 내 계정으로 복사(Fork)하려면 필요

설치가 안 되어 있다면:

- Git: https://git-scm.com/downloads 에서 다운받아 설치 (계속 "Next"만 눌러도 됩니다)
- Python: https://www.python.org/downloads/ 에서 다운받아 설치. **설치 화면에서 아래쪽에 있는
  "Add python.exe to PATH" 체크박스를 꼭 체크**하고 설치하세요.
- Node.js: https://nodejs.org 에서 "LTS"라고 써있는 버튼을 눌러 다운받아 설치

설치가 끝나면 제대로 됐는지 확인해봅니다. **PowerShell**(윈도우 검색창에 "PowerShell" 입력해서 실행)을
열고 아래 명령을 하나씩 입력해봅니다. 각 프로그램의 버전 번호가 나오면 성공입니다.

```powershell
git --version
python --version
node --version
```

## 1단계: 내 계정으로 저장소 복사하기 (Fork)

1. 브라우저로 원본 저장소 페이지에 들어갑니다: `https://github.com/jeseong77/etri-capstone`
2. 오른쪽 위의 **Fork** 버튼을 클릭합니다.
3. 잠시 기다리면 `https://github.com/내GitHub아이디/etri-capstone` 처럼 내 계정 밑에 똑같은
   저장소가 하나 생깁니다. 이제부터는 이 "내 것"으로 작업합니다.

## 2단계: 내 컴퓨터로 코드 내려받기 (Clone)

1. PowerShell을 엽니다.
2. 코드를 받아둘 폴더로 이동합니다. 예를 들어 바로가기 폴더로 가려면:

```powershell
cd C:\Users\내윈도우계정이름
```

3. 아래 명령으로 내 Fork 저장소를 내려받습니다. `내GitHub아이디` 부분만 실제 아이디로 바꿔주세요.

```powershell
git clone https://github.com/내GitHub아이디/etri-capstone.git
cd etri-capstone
```

성공하면 `etri-capstone`이라는 폴더가 생기고, 그 안에 `server.py`, `web_api.py` 같은 파일들이
보입니다.

## 3단계: Python 준비하기

AI 서버(`server.py`)를 돌리려면 Python 실행 환경을 하나 만들고, 필요한 부품(패키지)들을 설치해야
합니다.

1. `etri-capstone` 폴더 안에서, 전용 Python 환경을 만듭니다(다른 프로젝트와 부품이 섞이지 않게
   격리하는 것입니다):

```powershell
python -m venv .venv
```

2. 그 환경을 켭니다(활성화):

```powershell
.\.venv\Scripts\Activate.ps1
```

   성공하면 PowerShell 맨 앞에 `(.venv)`라는 표시가 붙습니다.

   > 만약 "실행할 수 없습니다" 같은 오류가 나오면, PowerShell을 관리자 권한으로 다시 열고
   > `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 를 입력한 뒤 다시 시도해보세요.

3. 필요한 부품들을 한 번에 설치합니다:

```powershell
python -m pip install -r requirements.txt
```

   화면에 여러 줄이 지나가고 마지막에 에러 없이 끝나면 성공입니다.

## 4단계: API 키 넣기 (.env 파일 만들기)

이 프로그램은 논문 검색을 위해 바깥 서비스(OpenAlex, arXiv, Semantic Scholar, Google Scholar)에
접속합니다. 이 서비스들 중 일부는 "API 키"라는 비밀번호 같은 것을 넣어줘야 더 안정적으로 동작합니다.

1. `etri-capstone` 폴더 맨 위에 `.env` 라는 이름의 새 파일을 만듭니다(메모장으로 만들어도 됩니다).
2. 그 안에 아래 내용을 붙여넣습니다.

```text
OPENALEX_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
SERPAPI_API_KEY=
```

3. 등호(`=`) 뒤에 본인이 발급받은 키가 있다면 붙여넣습니다. **키가 없어도 일단 실행은 됩니다** —
   다만 검색을 많이 하면 "요청이 너무 많습니다"라는 에러가 나올 수 있는데, 그럴 때 키를 넣으면
   해결됩니다.
   - `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`는 없어도 대부분 잘 됩니다.
   - `SERPAPI_API_KEY`는 Google Scholar 검색에 **꼭 필요**합니다. 키가 없으면 이 검색 기능만
     안 되고, 나머지(OpenAlex, arXiv, Semantic Scholar)는 그대로 잘 됩니다.
     키는 https://serpapi.com 에서 회원가입하면 무료로 받을 수 있습니다(월 250회까지 무료).
4. 파일을 저장합니다. (이 파일은 실수로 GitHub에 올라가지 않도록 이미 안전장치가 되어 있습니다.)

## 5단계: 서버가 잘 켜지는지 확인하기

PowerShell에서 (여전히 `(.venv)`가 앞에 붙어있는 상태로):

```powershell
python server.py
```

화면이 멈춘 것처럼 아무 반응이 없으면 **성공**입니다! 이 서버는 AI가 말을 걸어야 반응하는
방식이라, 혼자서는 아무것도 출력하지 않습니다. 화면에 빨간 글씨로 에러가 잔뜩 나오면 3~4단계를
다시 확인해보세요.

멈춰있는 걸 확인했으면 `Ctrl + C`를 눌러서 끕니다.

## 6단계: 웹사이트로 보기

웹사이트는 두 개의 프로그램을 **동시에** 띄워야 합니다. PowerShell 창을 **2개** 열어서 하나씩
실행합니다.

### 창 1: 뒷단(API) 서버 켜기

```powershell
cd C:\Users\내윈도우계정이름\etri-capstone
.\.venv\Scripts\Activate.ps1
python -m uvicorn web_api:app --port 8000
```

`Uvicorn running on http://127.0.0.1:8000` 같은 메시지가 나오면 성공입니다. 이 창은 **그대로
켜둔 채로 놔둡니다.**

### 창 2: 화면(프론트엔드) 켜기

새 PowerShell 창을 하나 더 열고:

```powershell
cd C:\Users\내윈도우계정이름\etri-capstone\frontend
npm install
npm run dev
```

`npm install`은 처음 한 번만 시간이 좀 걸립니다(1~2분). 끝나면 `npm run dev`가 실행되면서
`http://localhost:5173` 같은 주소가 화면에 나옵니다.

### 브라우저로 확인하기

브라우저를 열고 주소창에 `http://localhost:5173` 을 입력합니다. "OpenAlex 연구 지원 뷰어"라는
페이지가 보이면 성공입니다.

처음 받았을 때는 저장된 리포트가 없어서 "저장된 리포트가 없습니다"라고만 나올 수 있습니다 — 이건
정상입니다. 다음 단계에서 AI로 리포트를 만들어봐야 채워집니다.

두 창을 끄고 싶으면 각 창에서 `Ctrl + C`를 누르면 됩니다.

## 7단계(선택): AI와 연결해서 실제로 검색·저장해보기

이 부분은 Claude Desktop 같은, MCP를 지원하는 AI 프로그램이 있어야 할 수 있는 단계입니다. AI
설정 파일에 아래처럼 이 서버를 등록하면, AI가 논문을 검색하고 리포트를 저장할 수 있게 됩니다
(정확한 설정 방법은 사용하는 AI 프로그램의 안내를 따라주세요. 예시는 다음과 같은 형태입니다):

```json
{
  "mcpServers": {
    "openalex-research-assistant": {
      "command": "C:\\Users\\내윈도우계정이름\\etri-capstone\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\내윈도우계정이름\\etri-capstone\\server.py"]
    }
  }
}
```

등록한 뒤 AI에게 "OO 분야 논문을 찾아서 비교하고 리포트로 저장해줘" 같은 요청을 하면, 저장된
리포트가 6단계의 웹사이트에도 바로 나타납니다.

## 문제가 생겼을 때 (자주 발생하는 문제)

**"python은 내부 또는 외부 명령... 이 아닙니다" 라고 나와요**
→ Python 설치할 때 "Add python.exe to PATH"를 체크 안 한 경우입니다. Python을 다시 설치하면서
그 체크박스를 꼭 눌러주세요.

**"Port 5173 is in use" 라고 나와요**
→ 이미 다른 프로그램이 그 문(포트)을 쓰고 있다는 뜻입니다. 무시하고 그대로 진행해도, Vite가
자동으로 5174번 같은 다른 문을 대신 열어줍니다. 화면에 나온 실제 주소로 접속하면 됩니다.

**검색할 때 "HTTP 429" 나 "너무 많은 요청" 이라는 에러가 나와요**
→ 무료로 쓸 수 있는 횟수를 다 써버린 것입니다. 잠깐 기다리거나, 4단계에서 설명한 API 키를
넣으면 훨씬 여유롭게 쓸 수 있습니다.

**`.\.venv\Scripts\Activate.ps1` 실행이 안 돼요**
→ PowerShell을 마우스 오른쪽 클릭 → "관리자 권한으로 실행"으로 새로 열고, 아래 명령을 한 번만
입력한 뒤 다시 시도해보세요:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 요약: 다음에 또 실행할 때는

한 번 설치가 다 끝났다면, 다음번에는 이 부분만 반복하면 됩니다.

```powershell
cd C:\Users\내윈도우계정이름\etri-capstone
.\.venv\Scripts\Activate.ps1
python -m uvicorn web_api:app --port 8000
```

그리고 새 창을 하나 더 열어서:

```powershell
cd C:\Users\내윈도우계정이름\etri-capstone\frontend
npm run dev
```

그다음 브라우저에서 `http://localhost:5173` 을 열면 끝입니다.
