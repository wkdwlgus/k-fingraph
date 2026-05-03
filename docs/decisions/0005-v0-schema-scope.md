# ADR 0005: v0 그래프 schema 범위 결정 (Company + OWNS만 유지)

- Status: Accepted
- Date: 2026-05-03

## Context

v0 (MVP-zero) 진행 중 DART OpenAPI 도메인 학습 결과, 한국 금융 그래프를 풍부하게 표현하려면
다음 노드/엣지 타입이 추가로 필요하다는 점이 확인되었다:

- `Person` (임원·대주주) + `EXECUTIVE_OF` (임원 겸직)
- `Person`/`Institution` + `MAJOR_HOLDER_OF` (5%+ 대주주)
- `AuditFirm` + `AUDITED_BY` (회계감사인)
- `Event` (부도·회생·합병·분할 등 위기·구조 이벤트)
- 시계열 변동 정보 (최대주주 변동현황, 타법인 양수도 결정 등)

이 모든 신호가 들어가야 v3 충격 전파 시뮬레이션·v4 유사 종목 발굴·v5 포트폴리오 리스크
분석이 GraphRAG 도구로서 의미있는 결과를 낸다는 것이 명백하다.

핵심 질문: **v0 schema를 처음부터 확장해서 미래 도구에 대비할 것인가, 아니면 v0는
Company + OWNS만 유지하고 미래 노드/엣지는 해당 도구 sprint 진입 시점에 schema를
확장할 것인가?**

## Decision

**v0 schema는 `docs/schema.md`에 정의된 그대로 유지한다 — `Company` 노드 + `OWNS` 엣지만.**

미래 노드/엣지 타입은 해당 도구 sprint(v3·v4·v5) 진입 시점에 다음 절차로 추가한다:

1. 그 sprint의 KPI(예: 충격 전파 시뮬레이션의 백테스트 정확도)를 먼저 정의
2. KPI 달성에 필요한 신호를 식별
3. 필요한 노드/엣지 타입을 신규 ADR로 명시 (예: `0008-add-person-node-for-v3.md`)
4. `docs/schema.md`를 그 ADR과 함께 갱신
5. 그 sprint에서 적재할 DART API를 `docs/data-notes.md`의 미래 도구 카탈로그
   섹션에서 골라 학습 → 추출 → 적재

## Rationale

- **v0 sprint 보호**: v0는 7일 일정이며 목표는 "KOSPI 200 + 지분 그래프 + Cypher 3개 +
  Streamlit 시각화"이다. schema를 미리 확장하면 적재할 데이터 종류가 늘어나 sprint
  일정이 무너진다. CLAUDE.md의 "Don't add features beyond what the task requires" 원칙
  과 직접 일치.
- **YAGNI 위반 회피**: v3·v4·v5의 정확한 신호 요구사항은 그 sprint에서 KPI를 정의한
  뒤에야 확정된다. v0 시점에 추측으로 schema를 늘리면 잘못된 노드 모델로 락인될 위험.
- **점진적 검증**: Company + OWNS만으로도 v0 데모가 의미있는 그래프를 보여줄 수 있다는
  것은 입증 가능한 가설이다 (KOSPI 200 200건 × 정기보고서 기준 OWNS 138건+ × 200사 ≈
  수만 건의 엣지). 이 단순 그래프가 시각화·쿼리에서 어떻게 보이는지를 먼저 본 뒤,
  복잡도를 늘리는 것이 결정에 근거를 제공한다.
- **잊지 않을 안전장치**: v3·v4·v5 진입 시점에 어떤 API/신호가 필요한지는 이미
  `docs/data-notes.md`의 "향후 v3·v4·v5 진입 시 추가 학습 필요 API 카탈로그" 섹션에
  미리 박혀 있다. 즉 미래 확장은 망각되지 않는다 — 단지 시점이 미뤄질 뿐.

## Consequences

### 긍정

- v0 7일 일정 유지 가능
- 그래프의 가치를 단계적으로 증명하는 의사결정 흐름 확보
- 각 sprint마다 schema 변경이 ADR로 명시되어 변경 이력이 깔끔하게 추적됨

### 부정 / 비용

- v3 진입 시점에 schema 확장 + 데이터 재적재의 일회성 비용 발생 (단, v8 ops가
  도입되기 전이라 적재 cadence가 수동이므로 부담 작음)
- v0 데모가 단순해 보일 수 있음 — 그러나 이는 의도된 단순함이며 README와 v0 정의에
  명시되어 있음

### 후속 작업

- v3 진입 시: ADR `0008` 또는 그 시점 번호로 `Person` + `EXECUTIVE_OF` 추가 결정
- v4 진입 시: ADR로 `AuditFirm` + `AUDITED_BY` 추가 결정 (또는 v4의 신호 분석 결과에
  따라 다른 노드)
- v5 진입 시: 기존 노드 재활용 가능성 높음 — schema 변경이 작거나 없을 수도 있음
- 본 ADR은 이 후속 ADR들의 출발점 역할을 한다.
