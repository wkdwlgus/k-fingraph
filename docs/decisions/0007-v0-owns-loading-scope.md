# ADR 0007: v0 OWNS 엣지 적재 범위 — KOSPI 200 ↔ KOSPI 200

- Status: Accepted
- Date: 2026-05-03

## Context

v0 ingestion은 DART 두 응답에서 OWNS 엣지를 추출한다:

- **forward** (`otrCprInvstmntSttus`): 호출 회사가 출자한 타법인 목록. source는
  호출 회사의 corp_code(resolved), target은 피투자회사 이름 텍스트(`inv_prm`,
  unresolved).
- **reverse** (`hyslrSttus`): 호출 회사의 최대주주 + 특수관계인 목록. target은
  호출 회사의 corp_code(resolved), source는 주주 이름 텍스트(`nm`, unresolved).

`docs/data-notes.md`의 관찰 결과: forward만 해도 삼성전자 138건, SK하이닉스 49건의
타법인 출자 행이 응답된다. 그중 대부분은 비상장 자회사·외국 법인·SPC 등으로,
KOSPI 200 안에서 corp_code가 매칭되는 것은 일부에 불과하다. reverse도 마찬가지로
홀더에 외국 기관 투자자·개인·보험사·연기금이 다수 등장한다.

핵심 질문: **매칭 실패한 OwnsCandidate를 어떻게 처리할 것인가?**

- (a) 매칭 실패 후보는 적재 안 함. v0 그래프는 KOSPI 200끼리의 엣지만 가짐.
- (b) 매칭 실패 후보를 별도 노드 라벨(`:UnresolvedCompany` 등)로 적재. 그래프
  풍부하지만 schema에 새 노드 타입 추가 → ADR 0005 위배.
- (c) 매칭 실패 후보를 OWNS 엣지의 데드엔드 속성으로 보관. 그래프 표현 불가
  (Neo4j 엣지는 양 끝 노드가 필요).

## Decision

**(a) 매칭 실패 후보는 v0 그래프에 적재하지 않는다.**

구체:

- 추출 단계는 양방향 모두 수행. 결과는 `list[OwnsCandidate]`로 메모리 보유.
- 적재 직전(Day 4 Neo4j 적재 단계)에 필터:
  - `source.corp_code is not None and target.corp_code is not None`
  - 양쪽 모두 KOSPI 200사 corp_code 집합에 속함
- 위 조건을 통과한 후보만 `OwnsRelation`으로 승격하여 `MERGE`로 적재.
- 매칭 실패 후보는 카운트만 INFO 로그로 남기고 폐기 (v0 적재 후 통계 확인용).

## Rationale

- **ADR 0005 정신과 일치** — v0 schema는 `Company` + `OWNS`만. 비상장 자회사
  / 외국인 holder를 노드로 추가하려면 새 노드 타입이 필요하나 ADR 0005가 v0
  단순 유지를 결정.
- **Entity Resolution 미구현** — schema.md Open Questions의 "비상장 자회사",
  "외국 모회사" 처리는 v2 ER sprint의 결정 사안. v0에서 임시 처리하면 v2 진입
  시 재작업 비용 발생.
- **그래프 demo의 의도된 빈약함** — v0 정의(`README.md` 현재 상태 / `tasks/
  current.md` Definition of Done)는 "KOSPI 200 + 지분 그래프"이며, KOSPI 200끼리의
  교차 보유(예: 삼성생명 ↔ 삼성전자, 현대차 ↔ 기아, 금융지주 ↔ 자회사 은행)만으로도
  의미있는 hub-and-spoke 구조가 보일 것으로 예상. 풍부도 부족이 입증되면
  v1 또는 v2에서 확장.
- **Provenance는 보존됨** — 매칭 실패 후보도 추출 함수의 반환값에는 포함되어
  있으므로 적재 전 단계에서 카운트·샘플 로깅 가능. 폐기는 적재 시점에만 일어남.

## Consequences

### 긍정

- Day 3 추출 함수가 단순 — 매칭 여부와 무관하게 모든 행을 `OwnsCandidate`로 변환
- Day 4 적재 함수에 명확한 필터 책임이 박힘
- v0 그래프가 schema.md SSOT와 100% 정합

### 부정 / 비용

- v0 그래프의 노드·엣지 수가 적을 가능성 — 데모 인상이 약할 수 있음
- 매칭 실패 후보를 폐기하므로 같은 데이터를 v2 ER sprint 진입 시 다시 추출해야
  함 (cost: DART API 재호출 또는 fixture 재사용)

### 후속 작업

- Day 4 Neo4j 적재 함수 작성 시 본 ADR의 필터 정책을 코드에 명시 + 테스트
- v0 적재 후 매칭률 통계를 `docs/progress.md`에 기록 (실제 그래프 빈약도 측정)
- v2 ER sprint 진입 시 본 ADR을 supersede할 신규 ADR 작성 — 매칭 실패 후보의
  ER 처리 정책 + (필요 시) 신규 노드 타입 (Person / Institution / ForeignEntity 등)

## Supersedes / Superseded by

- 없음. ADR 0005(v0 schema 범위)의 운영 정책 보강.
