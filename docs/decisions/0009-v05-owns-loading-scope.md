# ADR 0009: v0.5 OWNS 적재 범위 — 확장 universe (KOSPI 보통주 + KOSDAQ 보통주)

- Status: Accepted
- Date: 2026-05-04

## Context

ADR 0007(v0)는 OWNS 엣지 적재 범위를 KOSPI 200 ↔ KOSPI 200으로 한정했다.
당시 결정의 근거는 `Company` + `OWNS` 단일 schema 정신(ADR 0005)과
"매칭 실패 후보의 처리 정책을 v0에서 임시로 박지 않는다"는 원칙이었다.

v0 1차 적재(2026-05-03)는 다음을 측정값으로 남겼다:

- 추출 후보 10,499건 → 적재 236건
- 폐기 후보 (A)/(B-1)/(B-2) 분류 = **A 338 / B-1 2,948 / B-2 6,964**
  (ADR 0008 측정 baseline)
- (A) "다른 상장사라서 매칭 실패한 것"은 ADR 0007 본문에서 v0.5 universe
  확장으로 회복될 것으로 예고됨

`tasks/backlog.md`의 v0.5 sprint 정의("적재 universe 확장: KOSPI 200 → 전체
KOSPI + KOSDAQ")가 이 supersede 작업의 트리거다. `docs/decisions/README.md`
인덱스의 "재검토 트리거" 컬럼이 이를 명시하고 있다.

전체 KOSPI / KOSDAQ universe를 KRX 정보데이터시스템에서 수집·정제한 결과:

- KOSPI 보통주 **839**개, KOSDAQ 보통주 **1,820**개, 합 **2,659** 회사
- DART corp_code 캐시 대비 매칭률 **100%** (2,659/2,659)
- 우선주·종류주권은 발행회사가 보통주와 corp_code를 공유하므로 정제
  단계에서 제외 (`주식종류 == 보통주`만 통과)

## Decision

**v0.5 OWNS 적재의 universe = `2,659개 보통주 발행 상장회사의 corp_code 집합`.**

ADR 0007의 적재 정책을 이 한 가지 점에서 supersede한다:

- 기존: `universe_corp_codes = {KOSPI 200 corp_codes}` (200개)
- 신규: `universe_corp_codes = {KOSPI 보통주 corp_codes ∪ KOSDAQ 보통주 corp_codes}` (2,659개)

ADR 0007의 나머지 정책은 그대로 유지된다:

- 적재 필터: `source.corp_code ∈ universe ∧ target.corp_code ∈ universe`
- 매칭 실패 후보는 (A)/(B-1)/(B-2)로 분류해 **카운트만** 보존하고 그래프
  적재는 안 함 (schema 단순성 유지)
- ADR 0008(엔드포인트 해소 정책: exact normalized-name match + universe
  priority + 비상장 corp_code 제외)도 변경 없음 — 단지 "universe priority"가
  가리키는 universe만 본 ADR이 정의한 새 universe로 교체

운영 영향: `src/k_fingraph/scripts/load_v05.py`가 신규 entry point.
`load_v0.py`는 v0 시점 frozen artifact로 삭제하지 않고 보존
(`data/processed/v0_load/report.json`과 짝).

## Rationale

v0.5 적재(`data/processed/v05_load/report.json`, 2026-05-04)는 ADR 0007이
예고한 (A) 회복을 정량 측정한다:

| 지표                           | v0 baseline | v0.5 측정 | 변화      |
| ------------------------------ | ----------- | --------- | --------- |
| Universe 회사 수               | 200         | 2,659     | +13×      |
| Candidates 추출                | 10,499      | 49,100    | +4.7×     |
| OWNS 적재(MERGE 후 그래프 엣지) | 242 → 236   | 2,378 → 2,347 | +9.9× |
| 그래프 Company 노드            | 200         | 2,659     | +13×      |
| **(A) 매칭 실패**              | **338**     | **181**   | **-46%**  |
| (B-1) 매칭 실패                | 2,948       | 16,553    | +5.6×     |
| (B-2) 매칭 실패                | 6,964       | 29,743    | +4.3×     |
| Walltime                       | ~3분        | 59분      | —         |

**(A) 회복은 부분 달성 — 잔여 181건의 정체.** ADR 0007 본문은 (A)를
"universe만 넓히면 매칭됨"으로 정의했으나, v0.5 universe로 확장한 뒤에도
181건이 (A)로 남았다. Sample을 보면 부산은행·경남은행·동양건설산업·
경남기업·쌍용건설 등으로, **상장폐지·합병 등으로 더는 KRX universe에 없지만
DART corpCode 표에는 historical `stock_code`가 보존된 corp_code들**이다.

이는 `extract/owns_diagnostics.py`의 (A) 분류 정의가 `stock_code is not None`
을 "currently listed"의 proxy로 사용한 데서 비롯되며, DART의 historical 보존
정책과 정합하지 않는다. v0.5에서 분류기를 수정하지는 않는다 (수정하면 v0
baseline과의 직접 비교가 깨짐). 대신 본 ADR이 잔여의 정체를 명시함으로써
"v0.5가 (A)를 다 잡지 못했다"는 인상이 잘못 박히지 않도록 한다.

**(B-1)/(B-2)의 절대치 증가는 universe 확장에 비례.** universe 13배 확장
대비 B-1·B-2는 각 5.6×·4.3× — 회사당 외부 텍스트 endpoint 수가 비슷한
분포를 가진다는 신호. 이는 v3 (Person)·v4 (AuditFirm) 등 schema 확장
sprint가 다룰 양적 베이스라인이 된다.

**OWNS 엣지 9.9× 증가의 의미.** v0의 hub-and-spoke 구조(삼성·현대차·금융지주
중심) 위에 KOSDAQ ↔ KOSPI 교차 보유 엣지가 다수 추가됐다 (구체 토폴로지
검증은 본 ADR 범위 밖 — Streamlit 워크벤치 또는 후속 분석 sprint).

## Consequences

### 긍정

- ADR 0007이 예고한 (A) 회복이 정량 입증됨 (-46%, 절대치 -157건)
- hub-and-spoke 외에 KOSDAQ ↔ KOSPI 교차 보유 엣지가 그래프에 처음 등장
- Universe 매칭률 100% (2,659/2,659) — DART corp_code 표가 KRX 보통주
  전종목을 빠짐없이 커버함을 확인. 우선주 필터링이 corp_code 중복을 정확히
  제거함도 같이 검증됨

### 부정 / 비용

- (A) 잔여 181건은 universe 확장으로는 영구히 해소 불가 (delisted +
  historical DART stock_code 구조). 본격 해소는 분류기 정의 갱신 또는
  v2 ER sprint 영역
- DART 호출 budget이 13배 증가 (v0 ~400콜 → v0.5 ~5,300콜). 0.5s 간격 유지
  시 walltime ~60분. 본 적재 패턴은 v1+ 데이터 갱신 cadence에서 재호출
  비용으로 누적될 것 — 향후 incremental update / 파트너 분기 캐시 등 검토
  대상 (현 sprint 범위 밖)
- Streamlit 워크벤치 selectbox 옵션이 200 → 2,659로 확장. UX 견딜 수
  있는지는 사후 체감 확인 필요 — 견디지 못하면 `_company_index.search_companies`
  활용한 autocomplete 패턴으로 별도 작업 단위에서 전환
- (B-1)/(B-2) 절대치 5×·4× 증가 — universe 확장에 비례하므로 surprise
  아님. 해소는 schema 확장 sprint(v3 Person, v4 AuditFirm, …) 영역

## Supersedes / Superseded by

- **Supersedes: ADR 0007** (v0 OWNS 적재 범위 — KOSPI 200 ↔ KOSPI 200).
  본 ADR은 ADR 0007의 universe 정의 한 점만 교체하며, 적재 필터·매칭 실패
  처리·ADR 0008(엔드포인트 해소) 정책은 그대로 승계
- v2 ER sprint 진입 시 본 ADR 함께 supersede 예상 (ADR 0008과 운명 공유 —
  매칭 실패 후보 처리 정책이 ER 정책으로 통합될 때)
