# Architecture Decision Records — Index

본 디렉토리는 K-FinGraph의 모든 Architecture Decision Record(ADR)를 보관한다.
**ADR은 결정의 이력(immutable log)이며, 일상 작업의 SSOT는 살아있는 문서**
(`docs/schema.md` / `docs/architecture.md` / `docs/conventions.md`)다. ADR은 "왜
이렇게 결정됐나"를 거슬러 올라갈 때, 또는 새 결정으로 옛 결정을 supersede할 때
펼친다.

## 어떻게 읽나

| 상황 | 어디부터 |
|---|---|
| 처음 프로젝트 진입 | 0001 → 0007 순서대로. 각 ADR 본문은 짧다 |
| 특정 결정의 근거 추적 | 살아있는 문서에서 cross-link된 ADR로 직접 점프 |
| 새 sprint 진입 | 아래 인덱스의 **재검토 트리거** 컬럼에서 본 sprint 이름이 등장하는 ADR을 펼침 |
| 결정을 뒤집는 새 ADR 작성 | 옛 ADR의 본문은 절대 수정하지 않음. 옛 ADR Status를 `Superseded by ADR 00YY`로 한 줄 갱신 + 새 ADR에 `Supersedes: ADR 00XX` 명시 |

## 인덱스

| #    | 제목                                                                  | Status   | Date       | 재검토 트리거                                                                          |
| ---- | --------------------------------------------------------------------- | -------- | ---------- | -------------------------------------------------------------------------------------- |
| [0001](0001-package-manager-uv.md) | Package Manager는 uv를 사용한다                                       | Accepted | 2026-04-27 | 없음 (생태계 급변 시 재검토)                                                            |
| [0002](0002-neo4j-aura-then-docker.md) | Neo4j는 Aura Free로 시작, 한계 도달 시 Docker로 전환                 | Accepted | 2026-04-27 | Aura 한도 75% 도달 / GDS 미지원 알고리즘 필요 / 쿼리 latency 5초+ (조건부)            |
| [0003](0003-llm-extraction-gpt4o-mini.md) | LLM 추출은 GPT-4o-mini만 사용한다                                    | Accepted | 2026-04-27 | 민감 정보 포함 필요 / API 비용 월 $50 초과 / 품질 부족 증거 (조건부)                  |
| [0004](0004-graphrag-positioning.md) | GraphRAG를 명시적 프레임으로 채택한다                                | Accepted | 2026-04-28 | 없음                                                                                   |
| [0005](0005-v0-schema-scope.md) | v0 그래프 schema 범위 = Company + OWNS만 유지                        | Accepted | 2026-05-03 | **v3 / v4 / v5 진입 시** schema 확장 신규 ADR 작성 (Person / AuditFirm 등)            |
| [0006](0006-owns-relation-type-thresholds.md) | OWNS 엣지의 `relation_type` 임계값 (50% / 20% / 0)                   | Accepted | 2026-05-03 | **v3 진입 시** 백테스트 정확도로 재검토 (`tasks/backlog.md` v3 섹션에 트리거 박힘)    |
| [0007](0007-v0-owns-loading-scope.md) | v0 OWNS 엣지 적재 범위 — KOSPI 200 ↔ KOSPI 200                       | Accepted | 2026-05-03 | **v0.5 진입 시** universe 확장으로 supersede / **v2 ER 진입 시** ER 정책 신규 ADR     |

## 트리거가 발화되는 메커니즘

위 표의 "재검토 트리거" 컬럼은 **약속**이지 자동 알림이 아니다. 실제 발화는
다음 두 경로 중 하나로 일어난다:

1. **sprint 진입 시 정독** — `/plan` 슬래시 명령 또는 사람이 새 sprint를 시작할
   때 본 인덱스의 트리거 컬럼을 훑어 본 sprint 이름이 등장하는 ADR을 펼친다.
2. **backlog 의 sprint 섹션** — `tasks/backlog.md`의 각 sprint 섹션에 "진입 전
   결정 재검토: ADR 00XX" 항목이 박혀 있으면 sprint를 `tasks/current.md`로
   이관할 때 함께 옮겨져 first-class 작업이 된다.

두 경로 모두 사람의 자율적 정독에 의존하므로 — **본 인덱스의 재검토 트리거
컬럼이 sprint 이름을 정확히 명시하는 것이 가장 중요하다.** 새 ADR이 미래
sprint 진입 시 재검토를 요구한다면 본 인덱스에 그 sprint 이름이 굵게 표시되어야
한다.

## 새 ADR 작성 시 절차

1. 다음 번호로 파일 생성: `00NN-짧은-슬러그.md`
2. 헤더 형식 (기존 ADR과 일치):
   ```markdown
   # ADR 00NN: 짧은 결정 제목

   - Status: Accepted
   - Date: YYYY-MM-DD

   ## Context
   ...
   ```
3. 본 인덱스의 표에 한 줄 추가 (#, 제목, Status, Date, 재검토 트리거)
4. 옛 ADR을 supersede하는 경우:
   - 새 ADR의 `## Supersedes / Superseded by` 섹션에 `Supersedes: ADR 00XX` 명시
   - 옛 ADR의 헤더 `Status: Accepted` → `Status: Superseded by ADR 00NN (YYYY-MM-DD)` 한 줄 갱신
   - 옛 ADR 본문은 변경하지 않음 (이력 보존)
   - 본 인덱스에서 옛 ADR의 Status 컬럼도 갱신
5. 살아있는 문서(schema.md / architecture.md / conventions.md) 중 영향받는 곳도
   동시 갱신 — ADR이 결정 이력이라면 살아있는 문서는 현재 상태이므로 정합성을
   맞춰야 한다.

## 외부 도구·모델 선택 ADR

위 절차에 더해, 외부 라이브러리·모델·인프라 선택은
[`docs/conventions.md`의 "외부 도구 선택 ADR 4단계"](../conventions.md) 원칙을
추가로 따른다. 평가 기준 정의 → 후보 survey → 정량 비교 → 결정 + Rationale 순.
