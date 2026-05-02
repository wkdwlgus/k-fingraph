# Current Sprint: v0 (MVP-zero) — 7일

목표: KOSPI 200 기업 노드 + DART 지분 엣지 적재, Cypher 3개 쿼리 통과,
Streamlit으로 그래프 시각화. 7일.

## Day 1: 환경 셋업

- [x] uv init, pyproject.toml, 의존성 설치
- [x] ruff/mypy/pytest 설정
- [x] `.env.example` + `config.py`
- [ ] Neo4j Aura Free 인스턴스 생성, 연결 핑
- [x] DART OpenAPI 키 발급, 핑 테스트 (e2e 테스트 `tests/e2e/sources/test_dart_corp_code_e2e.py`로 실호출 검증 완료)
- [x] 스모크 테스트 통과 (`tests/unit/test_smoke.py`)
- [x] GitHub repo public 생성, 초기 푸시
- [x] Day 1 회고 + progress.md 업데이트

## Day 2: DART 데이터 학습 + 수집

- [x] DART corp_code 전체 다운로드, 구조 파악 (`src/k_fingraph/sources/dart.py` + 스키마)
- [x] KOSPI 200 종목 리스트 확보 (KRX 또는 외부 source) — KRX 정보데이터시스템 CSV 수동 수집(2026-05-02 영업일 기준), `data/reference/kospi200.csv`로 저장
- [x] KOSPI 200에 대해 corp_code 매핑 (`src/k_fingraph/sources/kospi200.py`, 실데이터 매칭률 200/200 = 100%)
- [ ] DART 사업보고서 1~2건 직접 받아보고 지분 정보 위치 파악 (도메인 학습)
- [ ] notebook에서 탐색 → 발견사항을 `docs/data-notes.md`에 기록

## Day 3: 파싱 + Pydantic 스키마

- [ ] Pydantic: `Company`, `OwnsRelation`, `DartReport`
- [ ] DART 사업보고서 → 지분 관계 트리플 추출 함수
- [ ] 단위 테스트: fixture 기반 (실제 API 호출 없음)

## Day 4: Neo4j 적재

- [ ] Neo4j 클라이언트 래퍼 (`graph/client.py`)
- [ ] Constraint/index 마이그레이션 스크립트
- [ ] `MERGE` 기반 멱등 적재 함수
- [ ] 통합 테스트 (testcontainers)
- [ ] 실제 KOSPI 200 + 지분 데이터 1차 적재
- [ ] Neo4j Browser에서 육안 검증

## Day 5: 마일스톤 점검 + 쿼리 구현

- [ ] **점검**: 그래프에 데이터가 의미있게 들어갔는가? 빠진 부분은? 일정 재조정 필요?
- [ ] Cypher 쿼리 3종 구현 + 테스트
  - [ ] `get_subsidiaries(ticker)`
  - [ ] `find_common_parent(ticker_a, ticker_b)`
  - [ ] `get_within_2hop(ticker)`

## Day 6: Streamlit UI

- [ ] Streamlit 워크벤치 v0
- [ ] pyvis 그래프 시각화 컴포넌트
- [ ] 종목 검색 + 쿼리 3종을 드롭다운으로 노출
- [ ] 결과 표 + 그래프 + 출처 표시

## Day 7: 마감

- [ ] README.md 최종 정리 (스크린샷·실제 사용 예시 추가, v0 완료 상태 반영)
- [ ] `docs/troubleshooting.md`에 부딪힌 문제 ≥ 1개 기록
- [ ] `docs/progress.md`에 v0 완료 기록
- [ ] git tag `v0.1.0`
- [ ] v1 백로그 업데이트 → `tasks/current.md`에 v1 첫 스프린트 작성

## Definition of Done (v0)

- [ ] `uv run pytest -m "not e2e"` 0 fail
- [ ] `uv run ruff check . && uv run mypy src/` 0 error
- [ ] Streamlit 실행 → 종목코드 입력 → 그래프 시각화 동작
- [ ] 부딪힌 문제 ≥ 1개를 troubleshooting.md에 기록
- [ ] git tag `v0.1.0` + GitHub push

## Blocked / Questions

- DART API 연결성: 검증 완료 (e2e 테스트 통과).
- Neo4j Aura 연결 핑: 미검증 — Day 4 클라이언트 래퍼 작성 시 통합 테스트로 처리 예정.
