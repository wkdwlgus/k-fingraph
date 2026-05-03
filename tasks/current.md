# Current Sprint: v0 (MVP-zero) — 7일

목표: KOSPI 200 기업 노드 + DART 지분 엣지 적재, Cypher 3개 쿼리 통과,
Streamlit으로 그래프 시각화. 7일.

## Day 1: 환경 셋업

- [x] uv init, pyproject.toml, 의존성 설치
- [x] ruff/mypy/pytest 설정
- [x] `.env.example` + `config.py`
- [x] Neo4j Aura Free 인스턴스 생성 + `.env` 주입 (외부 키 발급 완료)
- [x] Neo4j Aura 연결 핑 — Day 4 적재 진입 시 검증 완료 (USERNAME/DATABASE/pause 이슈 해소 후)
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

## Day 3: 파싱 + Pydantic 스키마

- [x] Pydantic: `Company`, `OwnsRelation`, `DartReport`
  - `schemas/graph.py` 신규: `Company` / `OwnsEndpoint` / `OwnsCandidate` /
    `OwnsRelation` / `RelationType`. ER 전 상태 표현을 위해 `OwnsCandidate` +
    `OwnsEndpoint` 추가 (graph 적재되지 않는 ingestion 중간 산출물).
  - `schemas/dart.py` 확장: forward `DartOtherCorpInvestmentRow/Report`,
    reverse `DartMajorShareholderRow/Report`.
- [x] DART 사업보고서 → 지분 관계 트리플 추출 함수 (양방향)
  - `sources/dart_reports.py`: forward(`otrCprInvstmntSttus`) + reverse
    (`hyslrSttus`) fetcher + pure parser + 값 정규화 헬퍼
    (`parse_dart_int/float/pct/date`, `normalize_company_name`)
  - `extract/owns.py`: 두 방향 → `OwnsCandidate`. reverse 추출 시 stake_pct
    0/None 행은 특수관계인 명단으로 보고 제외. `classify_relation`은 ADR 0006
    임계값(50/20/0).
- [x] 단위 테스트: fixture 기반 (실제 API 호출 없음)
  - fixture 2종(`tests/fixtures/dart/otr_cpr_invstmnt_sample.json`,
    `hyslr_sttus_sample.json`) — edge case 망라(콤마/`-`/음수, 3가지 날짜
    포맷, 한자/괄호 법인형, 0지분 친인척)
  - `tests/unit/sources/test_dart_reports.py` + `tests/unit/extract/test_owns.py`,
    총 41건 신규 테스트 통과
- [x] 추출·적재 정책 ADR 2건 박음
  - ADR 0006: `relation_type` 임계값 + v3 재검토 트리거를 backlog v3 섹션에
    역참조 (잊지 않게)
  - ADR 0007: v0 OWNS 적재 범위 — KOSPI 200끼리 매칭되는 엣지만, 매칭 실패
    후보는 메모리에서 폐기. Day 4 적재 함수에서 필터로 박음.

## Day 4: Neo4j 적재

- [x] Neo4j 클라이언트 래퍼 (`graph/client.py`)
- [x] Constraint/index 마이그레이션 스크립트 (`graph/migrations.py`)
- [x] `MERGE` 기반 멱등 적재 함수 — ADR 0007 필터 적용 (`graph/load.py`,
  엣지 키 = `(source, target, source_id, as_of)` 복합)
- [x] 통합 테스트 (testcontainers) — 14건 통과
- [x] v0 Entity Resolution(`resolve/owns.py`) — universe 우선 + listed 보조,
  unlisted 의도적 제외 (ADR 0008로 박음). Plan B 진행 중 추가됨 — 이게 없으면
  모든 후보가 endpoint_unresolved로 drop되어 OWNS 적재 0건
- [x] 매칭 실패 후보 진단 분류기(`extract/owns_diagnostics.py`) + 단위 테스트
- [x] 실제 KOSPI 200 + 지분 데이터 1차 적재 — 회사 200, OWNS 236,
  resolver fix 587건. 결과 `data/processed/v0_load/report.json`
- [x] Neo4j Browser 육안 검증 — Cypher 샘플 쿼리로 hub-and-spoke 확인:
  삼성화재(out 12), 현대해상(out 12), 현대차(out 10) / 삼성전자(in 7).
  주요 SUBSIDIARY: LG화학→LG에너지솔루션 82%, 현대차→HMM 99.99%,
  HD한국조선해양→HD현대중공업 75%, 삼성생명→삼성카드 71.86%
- [x] 매칭 실패 후보를 (A)/(B-1)/(B-2)로 분류 카운트하여 `docs/progress.md`에
  기록 — A 338 / B-1 2,948 / B-2 6,964. v0.5 sprint 진입 시 비교 baseline
- [x] 트러블 2건 troubleshooting.md 등록 (Aura 자격증명 / DART percentage 필드)
  + CLAUDE.md 안티패턴에 한 줄 요약 반영

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
- [ ] v0.5 sprint(적재 universe 확장) 진입 — `tasks/backlog.md`의 v0.5 항목을
  `tasks/current.md`의 새 스프린트로 옮김. v1 진입은 v0.5 마감 후

## Definition of Done (v0)

- [ ] `uv run pytest -m "not e2e"` 0 fail
- [ ] `uv run ruff check . && uv run mypy src/` 0 error
- [ ] Streamlit 실행 → 종목코드 입력 → 그래프 시각화 동작
- [ ] 부딪힌 문제 ≥ 1개를 troubleshooting.md에 기록
- [ ] git tag `v0.1.0` + GitHub push

## Blocked / Questions

- 없음 (DART API · Neo4j Aura 연결 모두 검증 완료).
