# K-FinGraph

한국 금융 시장의 기업·인물·이벤트·관계를 지식 그래프로 구조화하고,
세 가지 분석 워크플로우를 그래프 알고리즘으로 결정론적으로 수행하는
금융 분석 인프라.

LLM과 경쟁하지 않는다. LLM이 한국 금융 질문에 답할 때 호출하는
신뢰 가능한 정량 레이어가 되는 것이 목표다.

## 무엇을 하는가

세 가지 도구를 제공한다 (Layer 2 — 실제 product):

| 도구 | 설명 |
|---|---|
| `simulate_shock(entity, scenario)` | 충격 전파 시뮬레이션 |
| `find_similar_stocks(ticker, top_k, similarity_type)` | 유사 종목 발굴 |
| `analyze_portfolio_risk(tickers, scenario)` | 포트폴리오 리스크 분석 |

이 도구들은 **GraphRAG 패턴** 위에서 동작한다. LLM은 비정형 텍스트(DART
공시, 뉴스)에서 그래프를 구축하는 indexing 단계에만 사용하고, 실제
분석(retrieval)은 Cypher / GDS 알고리즘으로 결정론적으로 수행한다.
자연어 답변 layer는 호출자 LLM(Claude / ChatGPT 등)이 우리 MCP 도구를
호출하는 방식으로 위임한다. 자세한 포지셔닝:
[ADR 0004](docs/decisions/0004-graphrag-positioning.md).

## 현재 상태

**v0 (MVP-zero) 진행 중** — 7일 스프린트.

- ✅ Day 1 — 코드 스캐폴딩 (pyproject, src/k_fingraph 모듈, 스모크 테스트)
- ⏳ Day 2~4 — DART 데이터 수집·파싱·Neo4j 적재
- ⏳ Day 5 — Cypher 쿼리 3종 (`get_subsidiaries`, `find_common_parent`, `get_within_2hop`)
- ⏳ Day 6 — Streamlit 워크벤치 (그래프 시각화)
- ⏳ Day 7 — 마감 (KOSPI 200 노드 + 지분 엣지 + 시각화 데모)

이후 로드맵(v1~v7): [tasks/backlog.md](tasks/backlog.md). 현재 스프린트
세부: [tasks/current.md](tasks/current.md).

## 아키텍처

```
Layer 3: Interfaces       Streamlit / MCP / FastAPI
Layer 2: Workflow Engine  3개 도구 (GraphRAG retrieval)
Layer 1: Graph Infra      Neo4j  +  LLM 추출 (GraphRAG indexing)  +  Entity Resolution
                            ↑ DART OpenAPI / 뉴스 RSS
```

자세한 데이터 흐름·모듈 경계·설계 원칙: [docs/architecture.md](docs/architecture.md).

## Quick Start

### Prerequisites
- Python 3.12
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Neo4j Aura Free 인스턴스, DART OpenAPI key, OpenAI API key
  — 발급 가이드는 [docs/setup.md](docs/setup.md)

### Install & Test

```bash
uv sync
cp .env.example .env   # 그다음 .env에 실제 키 채우기 (docs/setup.md 참조)

uv run ruff check .
uv run mypy src/
uv run pytest -x -m "not e2e"
```

E2E 테스트(실제 외부 API 호출, 비용 발생)는 별도:

```bash
uv run pytest -m e2e
```

## 프로젝트 구조

```
k-fingraph/
├── src/k_fingraph/
│   ├── config.py           환경변수 로딩 (Settings)
│   ├── errors.py           도메인 예외 (DartAPIError / LLMExtractionError / GraphWriteError)
│   ├── sources/            외부 데이터 fetch (DART, 뉴스)         · 예정
│   ├── extract/            LLM 기반 NER/RE (GraphRAG indexing)    · 예정
│   ├── resolve/            Entity Resolution                       · 예정
│   ├── graph/              Neo4j client + Cypher / GDS 래퍼        · 예정
│   ├── workflows/          Layer 2 — 3개 도구 구현                  · 예정
│   ├── interfaces/         Streamlit / MCP / REST                   · 예정
│   └── schemas/            Pydantic models                          · 예정
├── tests/
│   ├── unit/               외부 의존성 mock
│   ├── integration/        Neo4j testcontainer                     · 예정
│   ├── e2e/                실제 외부 API 호출                       · 예정
│   └── fixtures/           record-replay 데이터
├── docs/                   설계 문서
│   └── decisions/          ADR (변경 시 새 ADR 필수)
└── tasks/                  스프린트 관리 (current / backlog / done)
```

> "예정" 표시는 모듈 폴더와 빈 `__init__.py`만 있는 상태. v0 진행에 따라 채워진다.

## 문서

| 문서 | 내용 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 프로젝트 헌법 — Non-Negotiables, Anti-Patterns, Handoff Protocol |
| [docs/setup.md](docs/setup.md) | 처음 셋업 (외부 키 발급, `.env`, 첫 실행) |
| [docs/architecture.md](docs/architecture.md) | 3-layer 시스템 구조와 데이터 흐름 |
| [docs/schema.md](docs/schema.md) | 그래프 스키마 (살아있는 문서) |
| [docs/conventions.md](docs/conventions.md) | 코드 스타일·네이밍·테스트 정책 |
| [docs/testing.md](docs/testing.md) | 테스트 전략 (unit / integration / e2e) |
| [docs/progress.md](docs/progress.md) | 시간순 작업 로그 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 마주친 문제와 해결 기록 |
| [docs/decisions/](docs/decisions/) | ADR — 과거 결정 (재논의 금지, 변경은 새 ADR) |

## 기술 스택

- **Python 3.12**, **uv** ([ADR 0001](docs/decisions/0001-package-manager-uv.md))
- **Pydantic** v2 + **pydantic-settings** (스키마·환경변수)
- **ruff** + **mypy (strict)** + **pytest** (피드백 루프)
- **Neo4j** — Aura Free → Docker 단계적 전환 ([ADR 0002](docs/decisions/0002-neo4j-aura-then-docker.md))
- **OpenAI GPT-4o-mini** — LLM 추출 ([ADR 0003](docs/decisions/0003-llm-extraction-gpt4o-mini.md))
- (예정) **Streamlit**, **MCP**, **Neo4j GDS**, **httpx**, **Node2Vec**
