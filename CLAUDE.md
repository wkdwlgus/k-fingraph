# K-FinGraph

한국 금융 시장의 기업·인물·이벤트·관계를 지식 그래프로 구조화하고,
세 가지 분석 워크플로우를 그래프 알고리즘으로 결정론적으로 수행하는
금융 분석 인프라.

LLM과 경쟁하지 않는다. LLM이 한국 금융 질문에 답할 때 호출하는
신뢰 가능한 정량 레이어가 되는 것이 목표다.

## Three Tools (Layer 2 — the actual product)

1. `simulate_shock(entity, scenario)` — 충격 전파 시뮬레이션
2. `find_similar_stocks(ticker, top_k, similarity_type)` — 유사 종목 발굴
3. `analyze_portfolio_risk(tickers, scenario)` — 포트폴리오 리스크 분석

## Read These First (in order)

1. `docs/setup.md` — 처음 환경 셋업 시 (외부 키, .env, 첫 실행)
2. `docs/architecture.md` — 3-layer 시스템 구조와 데이터 흐름
3. `docs/schema.md` — 그래프 스키마 (살아있는 문서, 변경 시 ADR 필수)
4. `docs/conventions.md` — 코드 스타일·네이밍·테스트 정책
5. `docs/testing.md` — 테스트 전략 (mock vs real, 3-tier)
6. `tasks/current.md` — 지금 작업 중인 단위 (없으면 `docs/progress.md`로 직전 상태 파악)
7. `docs/decisions/README.md` — ADR 인덱스

## Non-Negotiables

- Python 3.12, package manager: **uv** (pip/poetry 사용 금지)
- 모든 추출 로직은 LLM API 없이도 테스트 가능해야 함 (mock mode 필수)
- Korean entity names: 원본 + 정규화형 둘 다 저장
- `.env`, `data/raw/`, Neo4j credentials는 절대 커밋 금지
- 새 노드 타입/엣지 타입 추가는 `docs/schema.md` 업데이트 + ADR 필수

## Feedback Loops (run before claiming done)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -x -m "not e2e"
```

E2E 테스트는 별도: `uv run pytest -m e2e` (실제 API 호출, 비용 발생)

## Anti-Patterns (learned the hard way)

이 섹션은 `docs/troubleshooting.md`에 새 사례가 기록될 때마다
한 줄 요약으로 추가한다.

- ❌ DART API 실호출을 단위 테스트에 넣지 말 것 — `tests/fixtures/` 사용
- ❌ Neo4j 쿼리에 사용자 입력 직접 보간 금지 — 파라미터화 쿼리만 사용
- ❌ LLM 추출 결과를 검증 없이 그래프에 적재하지 말 것 — Pydantic 스키마 통과 필수
- ❌ 한국 공공기관 다운로드 파일을 utf-8로 가정하지 말 것 — KRX·통계청 등은
  EUC-KR/CP949가 흔함. 인코딩 명시 + raw → 정제(UTF-8) 분리 저장

## Handoff & Plan (slash commands)

세션 종료 전 `/handoff` 실행. 새 작업 들어갈 때 `/plan` 실행 — 항상
plan → user confirm → execute 순서. 코드 변경 전 사용자 승인 필수.

### Sprint 진입 절차

본 프로젝트에서 sprint = version 단위 (v0 / v0.5 / v1 / ...). 새 sprint 진입 시:

1. `tasks/backlog.md`의 해당 sprint 섹션을 펼침 — 작업 단위 + "진입 전 결정
   재검토" / "진입 전 ADR 작성" bullet 모두 본다
2. 위 섹션 전체를 `tasks/current.md`로 이관 (header를
   `# Current Sprint: vN (sprint 이름) — 기간`으로 갱신).
   **"진입 전 결정 재검토"·"진입 전 ADR 작성" 류 bullet은 누락 없이 first-class
   작업으로 옮긴다 — 망각되면 결정 트리거가 발화되지 않음**
3. `docs/decisions/README.md` 인덱스의 "재검토 트리거" 컬럼에서 본 sprint
   이름이 등장하는 ADR을 모두 펼쳐 읽는다
4. 위 셋이 끝난 뒤 첫 작업 단위에 대해 `/plan` 시작
