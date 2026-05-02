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

## 다음 마일스톤

- [ ] **v0 (MVP-zero)**: KOSPI 200 노드 + 지분 엣지 + Cypher 3개 통과 + Streamlit 시각화 (목표 7일)
- [ ] v1: 뉴스 추출 파이프라인
- [ ] v2: Entity Resolution
- [ ] v3: 충격 시뮬레이터 + 워크벤치
- [ ] v4: 유사 종목 + 평가
- [ ] v5: 포트폴리오 리스크
- [ ] v6: MCP 서버 (GraphRAG 도구를 LLM에 노출)
- [ ] v7: GraphRAG vs Vector RAG 비교
