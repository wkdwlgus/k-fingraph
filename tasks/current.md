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
- [x] DART 사업보고서 1~2건 직접 받아보고 지분 정보 위치 파악 (도메인 학습) — 5개 엔드포인트(공시검색·기업개황·최대주주·타법인 출자·5% 보고)를 삼성전자·SK하이닉스로 호출, 응답 구조·결측 패턴·날짜 포맷 혼재 관찰
- [x] notebook에서 탐색 → 발견사항을 `docs/data-notes.md`에 기록 — notebook 대신 ad-hoc Python 스크립트로 탐색, 결과를 `docs/data-notes.md`에 (A)+(B 분리 대비) 설계로 정리, v3·v4·v5 미래 도구 API 카탈로그 포함

## 다음 세션 첫 액션 (Day 3 진입 전 선행)

- [x] **`docs/architecture.md` 정리** — Day 2 핸드오프 직후 stale 부분 발견됨 (2026-05-03 처리)

세 가지 gap을 처리 완료:

1. **Ingestion 흐름에 임베딩 단계 명시 누락** → Layer 1 다이어그램에
   `Graph Embedding (v4+)` 박스 신설, Entity Resolution 박스에 `v2+, 텍스트
   임베딩` 라벨, 본문에 신규 `### Embedding Pipelines` 섹션 추가 (텍스트 vs
   그래프 임베딩의 단계·목적·시점 비교표).
2. **LLM 추출 활성/비활성 시점** → 다이어그램 박스 라벨 `Extraction Pipeline
   (v1+, LLM-based)`로 변경, Ingestion 3번에 v0 skip / v1+ 활성 주석, Key
   Design Principles의 LLM 사용 범위 문구를 "v1부터"로 한정.
3. **ADR 0005의 점진적 schema 확장 반영** → 신규 `## Schema Evolution Timeline`
   섹션 (v0/v1/v3/v4/v5 별 추가 노드·엣지·트리거 KPI 표) + ADR 0005 cross-link
   + "v0 시점에 선제 확장 금지" 명시.

다음: Day 3 첫 단위(Pydantic `Company`·`OwnsRelation`·`DartReport` + 사업보고서
→ 트리플 추출 함수)로 진행.

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
