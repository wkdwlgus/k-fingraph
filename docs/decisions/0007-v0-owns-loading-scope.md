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

매칭 실패의 원인을 분리해서 다뤄야 한다 — "v2 ER이 들어오면 다 살아난다"는
잘못된 인상을 주지 않기 위함.

**(A) Universe 한계** — target/source가 상장사인데 v0 universe(KOSPI 200)에
없어서 매칭 실패. DART에 corp_code가 존재하므로 universe만 넓히면 매칭됨.
- **해소 경로**: `tasks/backlog.md`의 v0.5 sprint("적재 universe 확장: 전체
  KOSPI + KOSDAQ"). v0 마감 직후 진행 예정.

**(B-1) Schema 한계 (해소 가능)** — target/source가 회사가 아니거나 그래프 노드
타입에 없는 종류이지만, schema 확장으로 표현 가능. 비상장 자회사(corp_code 있는
경우), 임원·대주주 개인, 회계감사인, 일부 기관(국민연금 등) 등.
- **해소 경로**: 미래 schema 확장 sprint. `architecture.md` Schema Evolution
  Timeline에 일부 예고됨 — v3 진입 시 `Person` + `EXECUTIVE_OF`, v4 진입 시
  `AuditFirm` + `AUDITED_BY`. 모든 B-1이 망라되지는 않음 — 비상장사 일반·국내
  기관 일반은 아직 어떤 sprint에도 박혀 있지 않으며 필요 시점에 신규 ADR로 결정.

**(B-2) 진짜 데이터 한계 (영구 폐기)** — DART 응답이 텍스트 이상의 식별자를
주지 않으며 외부 보강 데이터 소스도 비현실적. 외국 법인(DART 외부), 익명
SPC·펀드·조합, 개인 친인척(PII).
- **해소 경로**: 없음. 그래프에 영구히 적재되지 않음.

**v2 ER sprint의 실제 효과** — (A)의 일부(이름 표기 차이로 매칭 실패한 경우)와
(B-1)의 일부(이름이 모호해서 노드 타입 결정 후에도 매칭 어려운 경우)를 해소.
**(A) 전체를 다 잡지는 않으며 (B-1)은 schema 확장이 선행되어야 의미 있음**.
즉 v2 ER만으로 v0 폐기 후보가 다 살아나지 않는다.

**비용 정리**:

- v0 그래프의 노드·엣지 수가 적을 가능성 — demo 인상이 약할 수 있음. v0.5에서
  (A)가 해소되면 대부분 회복됨.
- (B-1)에 해당하는 후보는 schema 확장 sprint마다 다시 추출해야 함 (DART API
  재호출 또는 fixture 재사용).
- (B-2)에 해당하는 후보는 v0뿐 아니라 미래 어떤 sprint에서도 영구히 폐기됨 —
  본 시스템의 표현 범위 밖에 있다는 점이 명시적으로 인정되어야 함.

### 후속 작업

- Day 4 Neo4j 적재 함수 작성 시 본 ADR의 필터 정책을 코드에 명시 + 테스트
- v0 적재 후 매칭률 통계를 `docs/progress.md`에 기록. 단순 매칭률(매칭/전체)이
  아니라 폐기 후보를 **(A) / (B-1) / (B-2) 분류 카운트**로 측정해야 행동 가능한
  정보가 됨:
  - (A): target/source 텍스트가 KOSPI 비-200 또는 KOSDAQ 종목명으로 추정되는
    것 (corpCode 표 안에서 corp_code 매칭은 되지만 KOSPI 200 universe에 없음)
  - (B-1): corpCode 표에서 corp_code가 매칭되지만 stock_code가 없음(비상장),
    또는 응답의 `relate` 필드가 "최대주주 본인"·"임원"·"특수관계인" 등 개인을
    시사
  - (B-2): 위 어느 패턴에도 안 맞는 자유 텍스트 (외국 법인명·익명 펀드 등)
- v0.5 sprint에서 universe 확장 후 위 통계와 비교 — (A)가 얼마나 줄었는지 정량
  측정. ADR 0007의 universe 정의를 v0.5에서 supersede.
- v2 ER sprint 진입 시 본 ADR을 supersede할 신규 ADR 작성 — 매칭 실패 후보의
  ER 처리 정책 + (필요 시) 신규 노드 타입 (Person / Institution / ForeignEntity 등)

## Supersedes / Superseded by

- 없음. ADR 0005(v0 schema 범위)의 운영 정책 보강.
