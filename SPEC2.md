# SPEC2: 논문 독립화 + Graph RAG 군집화

## Context

기존 `SPEC.md`는 논문을 리포트에 종속시켜 저장한다(리포트마다 참조 논문을 복사해서 저장, 리포트 간
공유 없음). 이번 확장은 논문별 요약(summary)과 임베딩을 기반으로 유사 논문을 그래프로 연결하고
군집화하기 위한 것으로, 이를 위해서는 논문이 여러 리포트에서 재사용되는 독립된 개체여야 한다. 따라서
논문을 리포트와 독립된 공유 라이브러리로 되돌린다.

## Goal

저장된 논문들 사이의 의미적 유사도를 계산해 군집을 만들고, 특정 논문과 관련된 다른 논문을 호스트
LLM이 즉시 찾아볼 수 있게 한다.

## Non-goals

- 실시간 군집 재계산 (배치 Tool로만 수행)
- 외부 임베딩 API 사용 (로컬 `sentence-transformers`만 사용)
- 커뮤니티 탐지(Louvain 등) 같은 정교한 그래프 알고리즘 (임계값 기반 connected components로 충분)
- 기존 로컬 `reports.db` 데이터의 자동 마이그레이션 (스키마 변경 시점에 사용자와 상호작용하며 별도로
  결정하기로 함 — 지금은 결정을 보류한다)

## User Flow (확장)

```text
연구 질문 → search_papers (OpenAlex 검색, 기존과 동일)
→ save_report (논문 + 요약 포함 저장 — 서버가 papers 테이블에 upsert, 임베딩 자동 계산)
→ (필요시) cluster_papers 실행 → 저장된 논문 전체를 유사도 기준으로 군집화
→ get_related_papers(paper_id) → 같은 군집의 다른 논문 조회
```

## Functional Requirements

- `papers`를 리포트와 독립된 공유 테이블로 전환한다 (openalex_id 기준 upsert, 여러 리포트가 같은
  논문 레코드를 공유).
- 논문 저장 시 `title + abstract`(또는 `summary`가 있으면 `title + summary`)로 로컬 임베딩
  (`sentence-transformers`, 예: `all-MiniLM-L6-v2`)을 자동 계산한다.
- 배치 Tool로 전체 논문 간 코사인 유사도를 계산해, 임계값 이상인 쌍만 엣지로 저장하고 connected
  components로 군집을 배정한다.
- 논문 하나를 기준으로 같은 군집 내 다른 논문을 유사도순으로 조회하는 Tool을 제공한다.

## Tool Contracts (변경/신규만 — 나머지는 SPEC.md와 동일)

| Tool | 변경 내용 |
|---|---|
| `save_report` | 입력 형식(`papers` 배열)은 동일, `summary` 필드 추가 지원. 내부적으로 각 paper를 `papers` 테이블에 `openalex_id` 기준 upsert하고, 임베딩이 없거나 오래됐으면 재계산한다. `report_papers`는 `(report_id, paper_id)` 순수 조인 테이블로 축소된다 |
| `list_papers` | `report_id` 필터는 유지하되, 이제 공유 테이블 기준으로 조회한다. 각 항목에 `cluster_id`를 포함한다 |
| `get_report` | 논문 목록을 조인 테이블을 통해 공유 `papers` 테이블에서 가져온다 (출력 형식은 동일) |
| `delete_paper(paper_id)` *(신규)* | 논문을 라이브러리에서 삭제한다. 참조 중인 리포트가 있으면 해당 `report_papers` 조인 행만 제거한다(리포트 본문 `content`는 그대로 유지되고, `get_report`의 papers 목록에서만 빠진다) |
| `cluster_papers(threshold?)` *(신규)* | 저장된 모든 논문의 임베딩을 코사인 유사도로 비교, `threshold`(기본 0.75) 이상인 쌍만 엣지로 저장한다. 엣지로 연결된 컴포넌트를 군집으로 배정하고 `papers.cluster_id`를 갱신한다. 실행마다 `paper_edges`를 전체 재계산(삭제 후 재삽입)한다. 군집별 논문 목록을 반환한다 |
| `get_related_papers(paper_id)` *(신규)* | 지정한 논문과 같은 `cluster_id`에 속한 다른 논문을 유사도순으로 반환한다. 군집이 아직 없으면(= `cluster_papers` 미실행) 에러를 반환한다 |

## Persistence Requirements (SQLite, 변경)

- `papers` (신규 독립 테이블): `id PK, openalex_id UNIQUE, title, publication_year, authors, doi, landing_page_url, cited_by_count, abstract, summary, embedding(JSON TEXT), cluster_id, updated_at`
- `report_papers`: `(report_id FK, paper_id FK)` 순수 조인 테이블로 축소한다 (기존의 논문 필드
  중복 저장을 제거)
- `paper_edges` (신규): `paper_id_a FK, paper_id_b FK, similarity REAL` — `cluster_papers` 실행마다
  전체 재계산한다 (기존 행 삭제 후 재삽입)

## Error Behavior

- 존재하지 않는 `paper_id` 참조 시 예외 대신 구조화된 에러를 반환한다 (기존 원칙 유지)
- `cluster_papers` 실행 전 `get_related_papers`를 호출하면 "아직 군집화되지 않았습니다" 형태의
  에러를 반환한다
- 저장된 논문이 1편뿐이라 유사 쌍이 없는 경우도 에러가 아니라 빈 결과로 처리한다

## Completion Criteria

- 같은 논문을 두 리포트에 각각 저장해도 `papers` 테이블에는 한 행만 생성된다 (중복 저장되지 않는다)
- `cluster_papers` 실행 후 `list_papers`에서 `cluster_id`가 채워진다
- 서로 관련된 논문(같은 주제) 2편 이상을 저장하고 군집화하면 `get_related_papers`로 서로를 찾을 수
  있다
- 논문 하나를 삭제해도 그 논문을 참조하던 리포트의 본문(`content`)은 그대로 유지된다

## Constraints

- 신규 의존성: `sentence-transformers` (torch 포함, 설치 용량이 큼) — `requirements.txt`에 추가
- 기존 `search_papers`, `list_reports`, `delete_report` 등은 동작 변경이 없다

## Assumptions

- 임베딩 대상 텍스트는 `title + abstract`이며, `summary`가 있으면 `title + summary`를 우선
  사용한다(초록보다 호스트 LLM 요약이 더 압축적이고 주제 대표성이 높다고 가정)
- 유사도 임계값 기본값 0.75는 잠정치이며, 실제 데이터로 확인하며 조정 가능하다

## Open Risks

- 기존 로컬 `reports.db`는 새 스키마와 호환되지 않는다. 이 SPEC 구현 시점에 사용자와 상호작용하여
  초기화할지 마이그레이션할지 결정한다 (지금은 결정을 보류한다)
- `sentence-transformers` 최초 설치·모델 다운로드 용량/시간이 상당하다 (수백MB, 첫 실행 시
  수십 초~수 분)
