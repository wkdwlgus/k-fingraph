# Progress Log

> 시간순 작업 로그. 매 세션 종료 시 한 줄 추가.

## 2026-04-27 (Day 0)

- 프로젝트 정의 및 SSOT 문서 셋업
- 서비스 정의 확정: 한국 금융 지식 그래프 + 3개 워크플로우 도구 + MCP 서버
- 로드맵 v0~v7 확정 (`tasks/backlog.md` 참조)
- ADR 0001~0003 작성 (uv / Neo4j Aura→Docker / GPT-4o-mini)
- 다음: dev 환경 셋업 (Day 1)

## 2026-04-28 (Day 1)

- 코드 스캐폴딩 완료 (`pyproject.toml` + `uv.lock`, ruff/mypy/pytest 설정)
- `src/k_fingraph/` 모듈 골격 생성 (config, errors + 7개 서브패키지 빈 `__init__.py`)
- `.env.example` + `tests/unit/test_smoke.py` 추가, 스모크 테스트 통과
- README 작성 + handoff 프로토콜에 README 동기화 단계 편입
- 남은 Day 1 항목: Neo4j Aura Free 인스턴스 + DART OpenAPI 키 발급(외부 작업)
- 다음: Day 2 — DART corp_code 다운로드 + KOSPI 200 매핑 (외부 키 발급 후 진입)

## 2026-05-02 ~ 2026-05-03 (Day 2 — DART 데이터 학습 + 수집)

- 외부 키 발급 완료(Neo4j Aura, DART OpenAPI), `.env`에 주입
- DART 기업 식별자(corpCode) 다운로더·파서·스키마 구현 + 단위 9건/e2e 1건 통과
- 다운로더 에러 분기(키 거부·HTTP 500·XML 없음·손상 ZIP) 단위 테스트 4건 추가,
  그래프 스키마 문서의 비상장 자회사 표현 정정
- KOSPI 200 종목 200건 수집(KRX 정보데이터시스템 수동 다운로드, EUC-KR → UTF-8
  변환, ticker+name 2컬럼 정제) → `data/reference/kospi200.csv`로 커밋
- KOSPI 200 ↔ DART corp_code 매핑 구현 + 단위 5건 통과, 실데이터 매칭률 200/200
- DART OpenAPI 5개 엔드포인트(공시검색·기업개황·최대주주·타법인 출자·5% 보고)
  도메인 학습 → `docs/data-notes.md` 작성. 단일 파일이지만 향후 디렉토리 분리가
  쉽도록 H2 단위 분리 가능 구조로 설계, 미래 도구 sprint(v3·v4·v5)에서 추가
  학습 필요한 API 카탈로그까지 포함
- e2e 테스트 5건 추가, 모두 실호출 통과
- 백로그 갱신: v8(정기 ingestion·운영 자동화) 추가, 잡일 풀에 유니버스 확장
  (전체 KOSPI + KOSDAQ) 추가
- `/question` 슬래시 명령어 신설(사이드 질문이 본 작업 흐름을 끊지 않도록)
- 핵심 발견(Day 3 파싱 단계 설계 시 반드시 반영): 회사 정식명 표기 차이
  (corpCode 표 vs company.json), 날짜 포맷 3종 혼재, 결측 표현 3종 혼재,
  소유 관계 응답의 비대칭성(호출 회사만 corp_code, 상대는 텍스트)
- Day 2 모든 항목 [x] 완료. 다음: Day 3 — Pydantic 스키마(`Company`,
  `OwnsRelation`, `DartReport`) + DART 사업보고서 → 지분 트리플 추출 함수
  + fixture 기반 단위 테스트
- 핸드오프 직후 발견: `docs/architecture.md`가 임베딩 단계 누락·LLM 활성
  시점 표시 누락·점진적 schema 확장 미반영으로 일부 stale. 다음 세션
  첫 액션으로 정리하기로 결정 (`tasks/current.md`의 "다음 세션 첫 액션"
  섹션 참조)

## 2026-05-03 (Day 3 — Pydantic 스키마 + 양방향 OWNS 추출)

- 그래프 스키마 모듈 신설(`schemas/graph.py`): `Company`(schema.md v0 9필드),
  `RelationType`(SUBSIDIARY/AFFILIATE/OTHER), `OwnsRelation`(graph 적재용),
  `OwnsEndpoint`+`OwnsCandidate`(ER 전 상태, graph에 적재되지 않는 중간 산출물)
- DART 정기보고서 두 응답에 대한 typed schema 확장(`schemas/dart.py`):
  forward(`DartOtherCorpInvestmentRow/Report`), reverse(`DartMajorShareholderRow/Report`)
- DART periodic report fetcher + pure parser(`sources/dart_reports.py`): 양방향
  fetch 함수 + JSON → typed report 변환. 값 정규화 헬퍼(콤마 숫자, 3종 날짜 포맷,
  3종 결측 sentinel, 음수 부호, 회사명 법인형 정규화) 같이 박음
- OWNS 추출(`extract/owns.py`): 두 방향 → `OwnsCandidate`. reverse는 stake_pct
  0/None 행을 특수관계인 명단으로 보고 제외. relation_type은 ADR 0006 임계값
  (50/20/0)으로 분류
- 결정 ADR 2건:
  - ADR 0006(OWNS relation_type 임계값) — K-IFRS 1110/1028 통상 추정 기준
    근거. v3 백테스트에서 분류 정확도 측정 후 재결정 — `tasks/backlog.md` v3
    섹션에 재검토 트리거를 박아 망각 방지
  - ADR 0007(v0 OWNS 적재 범위) — KOSPI 200 ↔ KOSPI 200만 그래프 엣지로
    승격, 매칭 실패 후보는 적재하지 않음. ADR 0005 정신("v0 단순 유지")과 정합
- fixture 2종 + 단위 테스트 41건 추가, 75건 모두 통과. ruff/format/mypy strict 통과
- 다음: Day 4 — Neo4j 클라이언트 래퍼 + Constraint/index 마이그레이션 + 멱등
  적재 + ADR 0007 필터 적용 + KOSPI 200 1차 적재 + Browser 육안 검증

## 2026-05-03 (Day 3 진입 선행 — architecture 문서 정리)

- `docs/architecture.md` stale 3건 해소: (1) Layer 1 다이어그램에
  `Graph Embedding (v4+)` 박스 신설 + `### Embedding Pipelines` 섹션
  (텍스트 임베딩 v2 vs 그래프 임베딩 v4 비교표), (2) Extraction Pipeline
  박스를 `v1+, LLM-based`로 라벨링하고 Ingestion 3번·Key Design Principles
  에 v0 skip / v1+ 활성 주석, (3) `## Schema Evolution Timeline` 섹션 신설
  (v0/v1/v3/v4/v5 별 추가 노드·엣지·트리거 KPI + ADR 0005 cross-link)
- 코드 변경 없음. ADR 신규 생성 없음 (기존 ADR 0004·0005 반영)
- 다음: Day 3 첫 단위 — Pydantic `Company`·`OwnsRelation`·`DartReport` +
  DART 사업보고서 → 지분 트리플 추출 함수 + fixture 단위 테스트

## 2026-05-03 (Day 4 — Neo4j 적재 + v0 ER + Aura 1차 적재)

- Neo4j 클라이언트 래퍼(`graph/client.py`): 환경변수 기반 driver lifecycle,
  session ctx, ping. Aura↔로컬 Docker 전환 시 코드 변경 없음 (ADR 0002 정합)
- 스키마 마이그레이션(`graph/migrations.py`): schema.md의 3개 DDL을 멱등 적용
  (Company.ticker UNIQUE, Company.corp_code UNIQUE, name_normalized INDEX)
- 멱등 적재(`graph/load.py`): `upsert_companies`(MERGE on ticker), `upsert_owns`
  (MERGE on `(source, target, source_id, as_of)` 복합 키 → 같은 공시 재적재
  멱등, 다른 시점은 별도 엣지로 보존). ADR 0007 필터(`filter_loadable_candidates`)는
  순수 함수로 분리 → Neo4j 없이 단위 테스트
- v0 Entity Resolution(`resolve/owns.py`): 텍스트 endpoint를 정규화 이름으로
  corp_code 표 lookup. universe(KOSPI 200) 우선 → listed 보조 → 미매칭은 그대로.
  unlisted corp_code는 의도적으로 인덱스에서 제외 (schema에 :UnlistedCompany
  없음 — 진단기가 B-1로 분류하도록 양보). architecture.md "v0 ER = 단순 키 매칭"
  정의 준수
- 매칭 실패 진단(`extract/owns_diagnostics.py`): ADR 0007 후속작업 정의 그대로
  (A)/(B-1)/(B-2) 분류 + 카테고리별 상위 5건 샘플 텍스트 보존
- 적재 스크립트(`scripts/load_v0.py`): KOSPI 200 → corp_code 캐시(없으면 다운로드)
  → DART forward+reverse fetch(200사 × 2엔드포인트, 0.5s 간격) → resolve →
  upsert → 진단 → JSON 리포트 stdout+파일. 단일 호출 실패는 isolation
- Day 4 통합 테스트: testcontainers Neo4j 5.23으로 client/마이그레이션/upsert
  멱등성·시점별 분리·필터 검증 14건 통과. Docker 미가동 환경에서는 graceful skip
- Aura 인스턴스 자격증명 정정: USERNAME이 "neo4j"가 아니라 인스턴스 ID
  (Aura 콘솔의 자격증명 .txt 파일 그대로). config 필드명을 `neo4j_username`으로
  통일하여 Aura 자격증명 파일을 그대로 .env에 붙여넣을 수 있게 정리.
  `.env.example` + 스모크 테스트 동기화
- Aura 1차 적재 결과(2026-05-03, `data/processed/v0_load/report.json`):
  - 회사 노드 200, OWNS 엣지 236 (적재 시도 242, 같은 공시키 중복 제거 6)
  - 후보 추출 10,499 / 적재 242 / endpoint_unresolved 9,919 / outside_universe 338
  - 진단 분류: **A 338 / B-1 2,948 / B-2 6,964** (ADR 0007 정의)
    - resolver 도입 전(분류기 단독 측정) → A 300 / B-1 3,235 / B-2 6,964.
      B-1 차이 287이 곧 universe 안으로 해소된 ER 갭이며 적재된 OWNS의 모집단
  - relation_type 분포: SUBSIDIARY 29 / AFFILIATE 84 / OTHER 123
  - 의미있는 hub 검출 사례: 삼성화재(out 12), 현대해상(out 12), 현대차(out 10),
    삼성전자(in 7) — KOSPI 200 내 cross-holding 구조가 잡힘
  - SUBSIDIARY 샘플(>=50%): LG화학→LG에너지솔루션 82%, 현대차→HMM 99.99%,
    HD한국조선해양→HD현대중공업 75%, 삼성생명→삼성카드 71.86%, POSCO홀딩스→
    포스코인터내셔널 70.7%, SK케미칼→SK바이오사이언스 66.45% — v0 demo로
    ADR 0007이 예상한 hub-and-spoke 구조 가시화
- 부딪힌 문제 → `docs/troubleshooting.md` 갱신 3건: (1) Aura USERNAME / DATABASE
  / 72h pause, (2) DART 응답에서 percentage 필드에 주식 수 등 out-of-range 값
  공시(영풍·삼성전자 일부) → loader 스크립트가 `DartParseError`도 회사 단위로
  isolation, (3) 1차 적재 OWNS 0건 — extract와 load 사이 식별자 해소 단계 누락이
  근본 원인, resolve 모듈 신설로 해소
- 다음: Day 5 — 마일스톤 점검 + Cypher 3종(`get_subsidiaries`,
  `find_common_parent`, `get_within_2hop`) 구현 + 테스트

## 2026-05-03 (Day 4 핸드오프)

- ADR 0008 작성 — 위 Day 4 섹션의 resolve 정책을 결정 기록으로 영구화. v0.5
  진입 시 (A)/(B-1)/(B-2) 재측정 트리거, v2 ER 진입 시 supersede 대상
- README v0 진행 상태 동기화(Day 4 ✅), 모듈 구조의 "예정" 마커 정리, 기술 스택
  보강(neo4j 드라이버·testcontainers)
- `current.md` Blocked / Questions 정리 (DART·Aura 모두 검증 완료)
- 다음 세션 진입 시 점검할 1회성 운영 메모 (트러블슈팅 본문에 적힌 내용은 제외):
  - 1차 적재 결과 JSON은 `data/processed/v0_load/report.json`에 보관
  - Day 5는 적재된 OWNS 위에서 동작하므로 데이터 적재 없이 바로 진입 가능

## 2026-05-03 (Day 5 — 마일스톤 점검 + Cypher 쿼리 3종)

- 마일스톤 점검: 회사 200·OWNS 236으로 v0 demo 신호량 충분, hub-and-spoke
  구조 육안 검증도 완료. 비상장 자회사(예: 삼성디스플레이) 누락은 ADR 0008에
  명시된 의도된 trade-off. 일정 재조정 불요 → Cypher/Streamlit 단계로 진행
- Cypher 쿼리 3종 구현 — `src/k_fingraph/graph/queries.py`:
  - `get_subsidiaries(ticker, relation_types=...)` — 1-hop OWNS 자식,
    기본 SUBSIDIARY만, 같은 (parent, child)에 시점 다른 엣지가 있으면
    최신 1개로 collapse
  - `find_common_parents(ticker_a, ticker_b)` — 두 종목을 모두 직접 보유한
    회사 (1-hop, 단수→복수 네이밍 변경: 공동 부모 N개 가능)
  - `get_within_2hop(ticker)` — 방향 무시 2-hop 유도 부분그래프
    (Streamlit 시각화 용도). 노드/엣지 분리 쿼리로 latest-as_of dedupe 단순화
- 결과 모델은 `src/k_fingraph/schemas/queries.py`로 분리 — Cypher Record가
  Streamlit/워크플로우 경계로 새지 않게 SubsidiaryRow / CommonParentRow /
  Subgraph(Node|Edge)로 projection
- 통합 테스트 13건 신규(testcontainers Neo4j) — 기본 동작·필터·미존재 ticker·
  고립 노드·시점 dedupe·다중 공통 부모 정렬·2-hop 양방향 reach 검증
- v0 작업 한계 2건 backlog에 first-class 트리거로 박음:
  - **v1 진입 시**: 시점 dedupe 정책 (현재 latest collapse) 재검토 — v1에서
    뉴스/지분공시로 시점 다양성 폭증
  - **v3 진입 시**: 쿼리 깊이·방향성 (현재 1-hop / 방향 무시) 재검토 —
    충격 전파는 transitive + 사이클 안전 traversal 필요
- 검증: ruff 0 / mypy 0 / pytest -m "not e2e" 136 passed
- 다음: Day 5 잔여 — 위 쿼리 함수의 Streamlit 어댑터(Day 6 같이 묶을지 고려),
  Day 6 — Streamlit 워크벤치 v0 + pyvis 시각화

## 2026-05-03 (Day 6 — Streamlit 워크벤치)

- 워크벤치 단일 페이지 구현 — `src/k_fingraph/interfaces/streamlit_app.py`.
  사이드바 라디오로 워크플로우 3종 분기, KOSPI 200 selectbox로 종목 선택,
  결과 표는 `st.dataframe`, 2-hop만 그래프 시각화. Neo4j 클라이언트는
  `@st.cache_resource`, 회사 인덱스는 `@st.cache_data`로 세션 내 1회 로드
- 시각화 라이브러리는 **pyvis가 아니라 Plotly + networkx**로 채택. 백로그에
  스캐폴딩 시점부터 박혀 있던 pyvis는 비교 없이 들어온 default였고, 다음
  근거로 갈아탐: (a) `st.plotly_chart`가 1급 시민이라 HTML 임베딩보다 정합성
  높음, (b) Plotly는 Streamlit 표준이라 v3 도구 시각화·인터랙션 확장 시
  코드 일관성 유지, (c) Plotly + networkx 모두 stdlib급 유지보수.
  v0 demo 단계에서 시각화 KPI를 정의할 수 없어 정식 ADR 4단계는 풀지 않고,
  v3 진입 시 인터랙션 요구가 분명해지면 정식 ADR로 supersede 결정. 트리거는
  `tasks/backlog.md` v3 섹션 "그래프 시각화 라이브러리 정식 선택"에 박힘
- `_viz.subgraph_to_plotly_figure` — networkx `spring_layout(seed=42)` 결정론
  배치 + relation_type별 색상 line trace + hover 정보 marker overlay + 방향
  화살표 annotation. center 노드는 gold + 큰 마커
- `_company_index` — Cypher 한 방으로 Company 200건 로드, ticker exact >
  prefix > name substring 우선순위로 검색 (지금은 selectbox만 쓰지만, universe
  확장 시 autocomplete 전환 부담 없게)
- 의존성 추가: `streamlit`, `plotly`, `networkx` + 외부 라이브러리 typed-marker
  부재로 mypy override 신설 (네 라이브러리 모두 ignore_missing_imports)
- 수동 브라우저 검증(localhost:8765, 실제 Aura 데이터):
  - 자회사 조회: LG화학 → LG에너지솔루션 81.84% (Day 4 검증값과 일치)
  - 공통 부모: 삼성전자 + 삼성바이오로직스 → 삼성물산 (한국 그룹 지배구조 상식)
  - 2-hop: 삼성화재 → 노드 47, 엣지 79, Plotly figure 79개 화살표 annotation
  - 사용 중 발견 — 공통 부모 패널의 selectbox default가 sorted-by-name 첫
    두 개(삼성물산·삼성바이오로직스)로 들어가 의도 없는 무결과를 보여줌 →
    placeholder 진입(미선택 시 안내 캡션)으로 패치
- 단위 테스트 13건 신규(`tests/unit/interfaces/`) — search 우선순위 8건 +
  Plotly figure 구조(빈 그래프·고립 center·다중 relation_type 색상 분리·
  화살표 annotation 수·center 색상 강조) 5건. 통합 테스트는 추가 없음
  (Streamlit UI 자체는 통합 테스트 영역 밖, 백엔드 쿼리는 Day 5에서 검증)
- 검증: ruff 0 / mypy 0 / pytest -m "not e2e" 149 passed
- `docs/setup.md`에 워크벤치 실행 명령(`uv run streamlit run ...`) 추가
- 다음: Day 7 — README/스크린샷 정리, troubleshooting.md 사례 보강, v0 완료
  태그(`v0.1.0`), v0.5 sprint 진입 절차

## 2026-05-03 (Day 7 — v0 마감)

- README 갱신 — 현재 상태를 "v0 진행 중 (Day 1~7 체크박스)"에서 **"v0 완료"**
  (KOSPI 200 그래프 + Cypher 3종 + Streamlit 가동)로 갈아끼움. 워크벤치 데모
  섹션 신설 + 스크린샷 3장(자회사 조회·공통 부모·2-hop) 임베드. 모듈 트리의
  interfaces 라인은 "예정"에서 "Streamlit 워크벤치 (v0)"로 갱신
- troubleshooting.md 신규 사례 — 워크벤치 selectbox default 조합으로 의도 없는
  무결과를 보여주는 UX 함정. CLAUDE.md 안티패턴에 한 줄 요약(다중 입력
  워크플로우는 placeholder + 명시적 선택 강제)
- v0 회고:
  - 7일 sprint 일정 안에 Definition of Done 모두 통과 (회사 200 / OWNS 236,
    Cypher 3종, Streamlit 가동, ruff/mypy 0, pytest -m "not e2e" 149 passed,
    troubleshooting 사례 ≥ 1)
  - 큰 함정 4건 모두 troubleshooting + 안티패턴화 — KRX EUC-KR / Aura
    USERNAME·DB·pause / DART percentage out-of-range / extract↔load 사이 ER 누락
    / 워크벤치 default UX
  - 결정 기록 8건 (ADR 0001~0008) — 그 중 v0 sprint에서 박힌 것은 0005~0008,
    재검토 트리거가 후속 sprint에 first-class로 박혀 있어 망각 위험 낮음
  - "demo가 손에 잡히는 신호"라는 v0 목적 달성 — KOSPI 200 안에서도 hub-and-spoke
    구조(삼성·현대·LG 그룹 지배구조)가 즉시 시각적으로 드러남
- v0.5 sprint 진입 — `tasks/current.md`를 v0.5 헤더로 갈아끼우고 backlog의
  v0.5 섹션 + 재검토 대상 ADR 0007/0008을 first-class 작업으로 이관 완료
- v0.1.0 annotated tag 생성. push는 사용자 확인 후

## v0.5 (적재 universe 확장)

- 2026-05-04 — KRX 정보데이터시스템에서 KOSPI·KOSDAQ 전종목 기본정보(EUC-KR)
  수집 → 보통주만 필터링하여 UTF-8 정제본(`data/reference/{kospi,kosdaq}_all.csv`)
  생성. 우선주·종류주권 제외(corp_code가 보통주와 중복되므로). 정제 결과:
  KOSPI 보통주 839 + KOSDAQ 보통주 1,820 = 2,659 회사 — KRX 대시보드의
  "회사수" 표시와 정확히 일치
- v0.5 universe 모듈(`sources/extended_universe.py`) 추가 — 시장 구분(KOSPI/
  KOSDAQ)을 행 수준에서 carry through. DART corp_code 캐시 대비 매칭률
  100% (2,659/2,659) 확인
- v0.5 적재 entry point(`scripts/load_v05.py`) 추가 — `load_v0.py`를 frozen
  artifact로 보존하면서 universe 진입점만 교체. 적재 필터·ER·분류 로직은
  v0 그대로 재사용
- 적재 결과(`data/processed/v05_load/report.json`, walltime 59분):

  | 지표                        | v0 baseline | v0.5     | 변화      |
  | --------------------------- | ----------- | -------- | --------- |
  | Universe 회사 수            | 200         | 2,659    | +13×      |
  | Candidates 추출             | 10,499      | 49,100   | +4.7×     |
  | OWNS 적재(그래프 엣지)      | 236         | 2,347    | +9.9×     |
  | 그래프 Company 노드         | 200         | 2,659    | +13×      |
  | **(A) 매칭 실패**           | **338**     | **181**  | **-46%**  |
  | (B-1)                       | 2,948       | 16,553   | +5.6×     |
  | (B-2)                       | 6,964       | 29,743   | +4.3×     |

- (A) 회복은 부분 달성 — 잔여 181건은 부산은행·경남은행·동양건설산업·쌍용건설
  등 **상장폐지됐지만 DART corpCode에 historical stock_code가 남아있는
  corp_code들**. classifier 정의가 `stock_code is not None`을 "currently listed"
  proxy로 사용한 데서 비롯되며 universe 확장으로는 영구 해소 불가.
  자세한 분석은 ADR 0009
- ADR 0009 신설(v0.5 universe 정의) — ADR 0007 supersede. ADR 0008은 supersede
  없이 baseline 비교만 수행 (v2 ER sprint에서 supersede 예정)
- 2026-05-04 세션 마감 — `v0.5.0` annotated tag 생성 + `git push origin
  main && git push origin v0.5.0` 완료. Streamlit selectbox 2,659 옵션 UX
  체감은 데스크톱 브라우저 직접 확인 필요해 sprint 안에서 닫지 못하고
  `tasks/backlog.md` 잡일 풀로 이관. 다음 sprint 미정 (v1 뉴스 추출 / v2 ER
  중 사용자 결정 대기)

## 다음 마일스톤

- [x] **v0 (MVP-zero)**: KOSPI 200 노드 + 지분 엣지 + Cypher 3개 통과 + Streamlit 시각화 (목표 7일)
- [x] **v0.5**: 적재 universe 확장 (KOSPI 보통주 + KOSDAQ 보통주, 회사 2,659 / OWNS 2,347, ADR 0009)
- [ ] v1: 뉴스 추출 파이프라인
- [ ] v2: Entity Resolution
- [ ] v3: 충격 시뮬레이터 + 워크벤치
- [ ] v4: 유사 종목 + 평가
- [ ] v5: 포트폴리오 리스크
- [ ] v6: MCP 서버 (GraphRAG 도구를 LLM에 노출)
- [ ] v7: GraphRAG vs Vector RAG 비교
