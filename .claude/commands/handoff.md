# /handoff — 세션 종료 전 문서 동기화

다음을 순차 실행하라:

## 1. `tasks/current.md` 점검 + 갱신 — 세 종류로 분리

### (α) 상태 점검
- 이번 세션에서 완료한 항목에 [x] 체크
- 막힌 항목이 있으면 `Blocked / Questions` 섹션에 명시
- 다음 세션이 바로 이어갈 수 있도록 in-progress 표기

### (β) 내용 점검 — 결정 변경의 task 전파
- 이번 세션에서 신설·변경된 결정을 한 줄씩 나열:
  - 신규 ADR 또는 ADR supersede
  - 살아있는 문서(`schema.md`/`architecture.md`/`conventions.md`) 갱신
  - `tasks/backlog.md` 변경
- 각 변경에 대해 미완 task(현재 sprint의 Day N + Definition of Done)
  중 영향받는 항목이 있는지 점검:
  - 영향 있으면 task 설명에 결정 반영 (ADR 번호 cross-link 권장)
  - 필요 시 새 task bullet 추가
  - obsolete된 task 제거
- 영향 없음을 확인한 경우 "결정 ↔ task 정합 OK"라고 명시 (확인했음을 기록)

### (γ) 위생 점검
- sprint 헤더 (`# Current Sprint: vN ...`)가 실제 현재 sprint와 일치하는가
- 일회성·임시 섹션("다음 세션 첫 액션" 등)이 처리 완료됐다면 제거 — 영구
  기록은 `docs/progress.md`에 두고 current.md에서는 정리
- 본 sprint의 Definition of Done이 모두 [x]면 sprint 전환 안내:
  `tasks/backlog.md`의 다음 sprint 섹션을 current.md로 이관
  (`CLAUDE.md`의 "Sprint 진입 절차" 따름)

## 2. `docs/progress.md`에 로그 추가

```
## YYYY-MM-DD
- 한 줄 요약: 무엇을 했나
- (선택) 다음 세션이 알아야 할 컨텍스트
```

## 3. 새 결정이 있었다면 ADR 작성 + 인덱스·살아있는 문서 동시 갱신

- `docs/decisions/000N-{topic}.md` 생성 (Context / Decision / Rationale / Consequences)
- **`docs/decisions/README.md` 인덱스 표에 신규 ADR 한 줄 추가** (#·제목·Status·Date·재검토 트리거). supersede 사례면 옛 ADR 행의 Status 컬럼도 갱신
- 살아있는 문서(`schema.md`/`architecture.md`/`conventions.md`) 중 영향받는 곳이 있으면 동시 갱신 — ADR이 결정 이력이라면 살아있는 문서는 현재 상태이므로 정합성을 맞춰야 한다

## 4. 트러블슈팅 사례가 있었다면 기록

- `docs/troubleshooting.md`에 증상/원인/해결/교훈 형식으로 추가
- 재발 방지를 위한 anti-pattern을 `CLAUDE.md`에 한 줄로 추가

## 5. `README.md` 동기화

- "현재 상태" 섹션의 Day/단계 진행 표기 갱신
- "프로젝트 구조"의 모듈별 "예정" 마커 — 실제 코드가 들어간 모듈은 제거
- "기술 스택"의 (예정) 항목 — 실제 도입한 라이브러리는 (예정) 제거
- 새 도구·새 외부 의존성·새 인터페이스 추가 시 해당 섹션 반영
- 어긋난 부분이 없으면 "README 변경 없음"이라고 보고

## 6. 변경된 파일 리스트를 사용자에게 제시

- `git status` 실행 결과 보여주기
- 커밋은 사용자가 직접 (메시지 제안은 가능)

## 7. 마무리

모든 작업 완료 후 한 줄 요약: "이번 세션에서 X 완료. 다음 세션은 Y부터."
