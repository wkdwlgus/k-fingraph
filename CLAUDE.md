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

## Current Phase

→ See `docs/progress.md` for what's done and what's next.
→ See `tasks/current.md` for the active sprint.

## Read These First (in order)

1. `docs/setup.md` — 처음 환경 셋업 시 (외부 키, .env, 첫 실행)
2. `docs/architecture.md` — 3-layer 시스템 구조와 데이터 흐름
3. `docs/schema.md` — 그래프 스키마 (살아있는 문서, 변경 시 ADR 필수)
4. `docs/conventions.md` — 코드 스타일·네이밍·테스트 정책
5. `docs/testing.md` — 테스트 전략 (mock vs real, 3-tier)
6. `tasks/current.md` — 지금 작업 중인 단위
7. `docs/decisions/` — 과거 결정 (재논의 금지, 변경은 새 ADR로)

## Non-Negotiables

- Python 3.12, package manager: **uv** (pip/poetry 사용 금지)
- Public 함수는 type hint 필수
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

## Handoff Protocol (세션 종료 전 필수)

1. `tasks/current.md` 체크박스 업데이트, 막힌 지점 명시
2. `docs/progress.md`에 한 줄 추가 (날짜 + 무엇을 했나)
3. 새 결정 있었으면 `docs/decisions/000N-*.md` 생성
4. 트러블슈팅했으면 `docs/troubleshooting.md`에 기록
5. 변경된 파일들 git add (커밋은 사용자가)

`/handoff` 슬래시 명령으로 자동화 가능.

## How to Plan New Work

새 작업 들어갈 때는 `/plan` 명령 사용. 작업 단위는 1~3시간으로 쪼갠다.
바로 코딩 들어가지 않는다. 항상 plan → user confirm → execute 순서.
