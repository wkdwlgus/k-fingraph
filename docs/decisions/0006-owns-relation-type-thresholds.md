# ADR 0006: OWNS 엣지의 `relation_type` 임계값

- Status: Accepted
- Date: 2026-05-03

## Context

`docs/schema.md` v0의 OWNS 엣지는 `relation_type` 필드를 enum으로 정의한다:
`SUBSIDIARY` / `AFFILIATE` / `OTHER`. 그러나 schema.md는 enum 값만 명시하고
**어떤 기준으로 셋을 가르는지**는 명시하지 않는다.

본 ADR은 v0 ingestion 단계에서 DART `otrCprInvstmntSttus` 응답의 `trmend_blce_qota_rt`
(기말 지분율 %)를 입력으로 받아 셋 중 하나로 분류하는 임계값을 박는다.

## Decision

**v0 분류는 단순 % 임계값**으로 한다:

| relation_type | 조건 (stake_pct는 0~100 범위) |
|---|---|
| `SUBSIDIARY` | `stake_pct >= 50` |
| `AFFILIATE`  | `20 <= stake_pct < 50` |
| `OTHER`      | `stake_pct < 20` 또는 `stake_pct is None` |

코드 상수로 박고(`extract/owns.py`의 `_classify_relation`), 별도 설정 없이 고정.

## Rationale

세 enum 값은 한국 회계기준(K-IFRS)의 분류에서 가져온 개념이며 임계값 또한
회계기준의 통상 추정 기준에서 가져왔다.

- **SUBSIDIARY (자회사, 지배 관계)** — K-IFRS 1110 「연결재무제표」.
  의결권 50% 초과 보유 시 지배력을 보유한다고 통상 추정. 자회사는 모회사의
  연결재무제표에 합산되어 매출·자산·부채가 통째로 인식되므로 충격 전파의
  강도가 가장 크다.
- **AFFILIATE (관계기업, 유의적 영향력)** — K-IFRS 1028 「관계기업과 공동기업에
  대한 투자」. 의결권 20% 이상 보유 시 유의적 영향력 추정. 지분법 적용 대상.
  한국 일상어 "관계사"·"계열사"는 공정거래법상 동일인 지배 그룹을 의미하기도
  하므로 본 enum 값의 의미는 회계상 관계기업으로 한정한다.
- **OTHER (단순 투자, 영향력 없음)** — K-IFRS 1109 「금융상품」. 영향력 없는
  지분 보유. 공정가치 평가. 운영 결합도 약함.

본 % 임계값은 회계기준의 **통상 추정** 기준이며 실제 K-IFRS 적용은 % 외에
실질 지배력·영향력 판단을 종합 요구한다 (예: 30% 보유여도 이사회 과반 임명
권한이 있으면 자회사가 될 수 있음). v0는 단순 % 휴리스틱으로 시작하며,
정확한 분류가 필요하면 v3 충격 전파 시뮬레이션 sprint에서 재결정한다.

`stake_pct`가 `None`인 경우(DART 응답의 `"-"` / `""` 결측) `OTHER`로 분류한다 —
영향력 추정 불가능 시 가장 약한 분류가 안전 기본값.

## Consequences

### 긍정

- v0 그래프에서 OWNS 엣지의 강도를 색깔·굵기로 구분 시각화 가능
- ADR로 박힘으로써 미래 자기·외부 협업자가 임의 변경을 막을 수 있음
- v3 진입 시 재검토 트리거가 명시됨

### 부정 / 비용

- 실제 K-IFRS 분류와 차이 가능 (소수 케이스에서 SUBSIDIARY로 분류해야 할
  것을 AFFILIATE로 분류하거나 그 반대). v0 demo 수준에서는 허용 오차.
- DART 응답의 `invstmnt_purps`(출자 목적: "경영참여"/"단순투자") 필드를 v0에서
  사용하지 않음 — 회사 자신의 분류 정보를 무시. v3 진입 시 이 필드를 같이 보는
  것이 정확도 향상 후보.

### 후속 작업

- v3 sprint 진입 시 본 임계값을 KPI(백테스트 정확도)에 따라 재검토.
  대안: `invstmnt_purps` 텍스트 정규화 + 임계값 조합, 또는 별도 enum 값
  (`PARTICIPATING` / `PASSIVE`) 추가.
- 본 임계값 변경 시 새 ADR로 supersede.

### 재검토 트리거 (잊지 않게)

본 ADR의 v3 재검토 약속은 `tasks/backlog.md`의 v3 섹션 "진입 전 결정 재검토"
항목에 박혀 있다. v3 sprint 진입 시 그 항목이 실행 트리거 역할을 한다.
backlog에서 본 ADR 번호가 빠지면 안 된다 — 약속이 망각된다.

## Supersedes / Superseded by

- 없음. ADR 0005(v0 schema 범위)와 보완 관계 — schema.md의 enum을 운용에
  필요한 임계값까지 확정.
