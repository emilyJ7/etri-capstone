# SPEC4: 다중 소스 논문 검색 (arXiv, Semantic Scholar, Google Scholar)

## Context

OpenAlex는 논문에 따라 초록을 제공하지 않는 경우가 있어(`SPEC.md` 구현 이후 실제로 겪은 문제),
제목·게재지만으로는 깊이 있는 비교 분석이 어렵다. 이를 보완하기 위해 다른 논문 데이터 소스를
추가로 연계한다.

## Goal

arXiv, Semantic Scholar, Google Scholar를 추가로 검색할 수 있게 하여, OpenAlex에 초록이 없는
논문도 다른 소스에서 초록을 확보하거나, 애초에 더 풍부한 정보를 가진 소스에서 논문을 찾을 수 있게
한다.

## Non-goals

- **Google Scholar 직접 스크래핑**: 공식 API가 없고, 직접 스크래핑은 Google 이용약관 위반이며
  캡차/IP 차단으로 불안정하다. 대신 이 리스크를 서비스 제공자가 감수하는 유료 서드파티
  SerpApi를 경유해서만 연동한다.
- **소스 간 자동 병합·중복 제거**: 소스별로 별도 Tool을 제공하고, 병합·중복 판단은 호스트 LLM의 몫으로
  남긴다.
- **기존 `search_papers`(OpenAlex) 동작 변경**: 기존 Tool의 입출력 계약은 그대로 유지한다(단, 결과에
  `source` 필드가 추가된다).

## Tool Contracts (신규)

| Tool | 입력 | 출력 |
|---|---|---|
| `search_arxiv` | `query` (str), `limit?` (int, 기본 5, 최대 10), `sort?` ("relevance" \| "date", 기본 relevance), `category?` (str, 예: "cs.CL") | 논문 목록: `openalex_id`(arXiv URL), `title, publication_year, authors, doi(항상 null), landing_page_url, cited_by_count(항상 null), abstract, source("arxiv")` |
| `search_semantic_scholar` | `query` (str), `year_from?` (int), `year_to?` (int), `limit?` (int, 기본 5, 최대 10), `sort?` ("relevance" \| "citations", 기본 relevance) | 논문 목록: `openalex_id`(Semantic Scholar paperId), `title, publication_year, authors, doi, landing_page_url, cited_by_count, abstract, source("semantic_scholar")` |
| `search_google_scholar` | `query` (str), `year_from?` (int), `year_to?` (int), `limit?` (int, 기본 5, 최대 10), `sort?` ("relevance" \| "date", 기본 relevance) | 논문 목록: `openalex_id`(SerpApi result_id), `title, publication_year, authors, doi(항상 null), landing_page_url, cited_by_count, abstract(스니펫), source("google_scholar")` |

`save_report`는 변경 없이 그대로 사용한다 — 어느 검색 Tool에서 나온 논문이든 동일한 필드 구조라
`papers` 배열에 그대로 넣어 저장할 수 있다.

## Google Scholar (SerpApi) 관련 특이사항

- **필수 API 키**: `search_google_scholar`는 다른 세 Tool과 달리 키 없이는 아예 동작하지 않는다.
  `SERPAPI_API_KEY`가 없으면 요청을 보내지 않고 바로 구조화된 에러를 반환한다.
- **유료 서비스**: SerpApi는 Google 검색결과 페이지(SERP)를 대신 스크래핑해서 파는 상업 서비스다.
  무료 플랜은 월 250회, 이후 월 $25(1,000회)부터 유료 플랜이 시작된다. 직접 만든 스크래퍼가 아니라
  이용약관 위반 리스크를 SerpApi가 대신 지는 구조라는 점에서 직접 스크래핑과는 다르지만, 여전히
  Google 공식 채널은 아니다.
- **월 사용량 자체 제한**: 무료 플랜(월 250회)을 실수로 넘겨 과금되는 일이 없도록, 서버가 자체적으로
  이번 달 호출 횟수를 세어 `SERPAPI_MONTHLY_LIMIT`(기본 250, `.env`로 조정 가능)에 도달하면 SerpApi에
  요청을 보내지 않고 바로 에러를 반환한다. SerpApi 쪽 자체 한도가 아니라 우리 쪽에서 선제적으로
  차단하는 것이라, 유료 플랜으로 올리면 `.env`의 `SERPAPI_MONTHLY_LIMIT` 값만 올리면 된다.
- **abstract는 스니펫**: Google Scholar 검색 결과 자체가 전체 초록을 제공하지 않기 때문에,
  `abstract` 필드에는 검색 결과에 나오는 2~3줄짜리 스니펫만 들어간다. 다른 세 소스의 `abstract`와
  품질이 다르다는 점을 호스트 LLM이 인지해야 한다.
- **발행 연도 추출**: SerpApi 응답에는 별도 연도 필드가 없고, `publication_info.summary` 문자열
  (예: `"ZH Zhou - 2021 - books.google.com"`)에서 4자리 연도를 정규식으로 추출한다. 저자명에 연도처럼
  보이는 4자리 숫자가 섞여 있는 드문 경우 오추출 가능성이 있다.

## 필드 재사용에 대한 설계 결정

`openalex_id`라는 필드/컬럼명을 그대로 재사용해 arXiv ID, Semantic Scholar paperId, SerpApi
result_id를 담는다. 이름이 정확히 맞진 않지만("OpenAlex" 전용처럼 보임), 다음 이유로 이름을
바꾸지 않았다:

- 이름을 바꾸려면 `report_papers` 테이블 컬럼, `save_report`/`get_report`/`list_papers` 응답,
  프론트엔드(`ReportDetail.jsx`의 React key) 등 여러 곳을 함께 고쳐야 한다.
- 이 필드는 실질적으로 "출처 시스템에서 논문을 가리키는 고유 식별자" 슬롯으로 쓰이고 있고, 새로
  추가된 `source` 필드가 실제 출처를 명확히 구분해 주므로 혼동 위험은 낮다.

## Persistence (SQLite, 변경)

- `report_papers`에 `source TEXT` 컬럼을 추가한다
  (`"openalex"`, `"arxiv"`, `"semantic_scholar"`, `"google_scholar"`).
- 기존 테이블에는 **`ALTER TABLE ... ADD COLUMN`으로 마이그레이션**한다(`CREATE TABLE IF NOT EXISTS`는
  이미 존재하는 테이블에 새 컬럼을 추가해주지 않으므로, `_init_db()`에서 `PRAGMA table_info`로 컬럼
  존재 여부를 확인한 뒤 없으면 추가한다). 기존 저장된 리포트/논문 데이터는 그대로 보존되고, 마이그레이션
  이전에 저장된 논문의 `source`는 `NULL`이 된다(호출부에서는 `"openalex"`로 취급).
- `api_usage(source, period, count)` 테이블(신규)에 소스별·월별(`YYYY-MM`) 호출 횟수를 기록한다.
  `search_google_scholar`가 실제로 SerpApi에 요청을 보내기 직전에 이 카운트를 확인·증가시킨다.
  월이 바뀌면 새 `period` 값으로 자동 리셋된다(과거 월 기록은 남아있지만 조회하지 않는다).

## Error Behavior

- 4개 검색 Tool 모두 기존 `search_papers`와 동일한 패턴: 빈 검색어·잘못된 sort 값은 예외 대신
  구조화된 에러(`{"query":..., "error":..., "papers":[]}`)로 반환한다.
- 외부 API 오류(HTTP 오류, 연결 실패, arXiv 응답 파싱 실패, SerpApi 오류 응답)도 동일하게 구조화된
  에러로 반환한다.
- `search_google_scholar`는 `SERPAPI_API_KEY` 미설정 시에도 예외 없이 안내 메시지를 담은 에러를
  반환한다.

## 확인한 내용

- `search_arxiv`: 실제 API로 검색해 초록이 포함된 결과를 확인했다.
- `search_semantic_scholar`: 코드 경로(에러 처리 포함)는 정상이지만, 이 환경의 공유 IP가 Semantic
  Scholar의 비인증 요청 한도(429)에 걸려 실제 데이터 검색은 확인하지 못했다. 원본 API 응답을 직접
  확인해 레이트리밋이 맞다는 것은 검증했다.
- `search_google_scholar`: 키가 없는 상태에서 에러 처리, 빈 검색어/잘못된 sort 검증을 확인했다.
  실제 SerpApi 데모 페이지에서 가져온 샘플 응답으로 파싱 로직(`_parse_scholar_result`)을 오프라인
  검증했다 — 연도 추출, 저자명, 인용수, 메타데이터가 아예 없는 항목까지 정상 처리됨을 확인했다.
  단, 발급받은 실제 키로 라이브 호출까지는 확인하지 못했다.
- 월 사용량 제한: 가짜 키로 사용량을 248회부터 시작해 249·250번째 호출은 실제로 SerpApi에 요청을
  보내고(가짜 키라 401 응답), 251번째 호출은 SerpApi에 요청을 보내지 않고 우리 쪽 한도 에러를
  즉시 반환하는 것을 확인했다. 테스트 후 사용량 카운터는 0으로 되돌려 놓았다.
- arXiv/Google Scholar 출처 논문을 `save_report`로 저장 → `get_report`/`list_papers`에서
  `source` 값이 올바르게 유지되는 것을 확인했다.
- 마이그레이션 후에도 기존 실제 리포트(1건, 논문 4편)가 그대로 보존되는 것을 확인했다.
- 프론트엔드(`PapersList`, `ReportDetail`)에 출처를 보여주는 작은 배지(`SourceBadge`)를 추가했다
  (OpenAlex/arXiv/Semantic Scholar/Google Scholar 4종 라벨).

## Semantic Scholar 재시도(백오프)

`_fetch_json_with_backoff()` 헬퍼를 추가해 `_search_semantic_scholar`가 HTTP 429를 받으면 지수
백오프(1s, 2s, 4s, 최대 3회 재시도)로 재시도한다. 응답에 `Retry-After` 헤더가 있으면 그 값을
우선 사용한다. 로컬 테스트 서버로 (1) 429 두 번 뒤 200 성공, (2) 계속 429라 재시도 소진 두 경우
모두 정상 동작을 확인했다. 다만 이 환경의 공유 IP는 재시도를 다 써도 여전히 429가 발생할 만큼
이미 한도를 초과한 상태라, 실제 API에서 재시도 후 성공하는 것까지는 확인하지 못했다(로컬 시뮬레이션
으로는 로직 자체가 올바름을 검증함).

## Open Risks

- Semantic Scholar의 비인증 요청 한도가 낮아(공유 IP 환경에서는 더욱 그렇다) 실제 사용 시 429가
  잦을 수 있다. API 키 발급을 권장한다.
- arXiv API는 검색어를 단순 `all:` 필드 검색으로만 다룬다 — 저자명, 제목 한정 검색 같은 세부 필터는
  지원하지 않는다(필요해지면 `ti:`, `au:` 같은 필드 지정자를 노출하는 확장을 검토한다).
- `search_google_scholar`는 실제 SerpApi 키로 라이브 호출 검증이 안 되어 있다 — 키를 발급받은 뒤
  한 번 실제 호출로 확인해 보는 것을 권장한다.
- SerpApi는 유료 서비스이므로, 무료 월 250회를 넘기면 비용이 발생한다는 점을 사용 전 인지해야 한다.
