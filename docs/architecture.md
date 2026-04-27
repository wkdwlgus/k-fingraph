# Architecture

## 3-Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Interfaces                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Streamlit UI │  │  MCP Server  │  │ FastAPI REST │  │
│  │ (workbench)  │  │ (LLM-facing) │  │ (dev-facing) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼──────────┘
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Workflow Engine (3 tools)                      │
│  - simulate_shock()                                     │
│  - find_similar_stocks()                                │
│  - analyze_portfolio_risk()                             │
│                                                         │
│  이 도구들은 GraphRAG 파이프라인의 retrieval 단계에      │
│  해당한다 (LLM 호출은 indexing 단계의 추출에 국한,      │
│  답변 생성에는 사용하지 않으며 자연어 layer는 호출자    │
│  LLM에 위임).                                            │
└────────────────────────────┬────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Graph Infrastructure                           │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Neo4j     │  │  Extraction  │  │  Entity        │  │
│  │  (Aura→    │←─│  Pipeline    │←─│  Resolution    │  │
│  │  Docker)   │  │  (LLM-based) │  │                │  │
│  └────────────┘  └──────┬───────┘  └────────────────┘  │
│                         ▼                               │
│         ┌───────────────────────────────┐               │
│         │  Data Sources                 │               │
│         │  - DART OpenAPI               │               │
│         │  - News (RSS, TBD)            │               │
│         └───────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

### Ingestion (write path)
1. Source fetch (DART API / news RSS) → `data/raw/`
2. Parser → structured records (Pydantic)
3. LLM extractor (NER + Relation Extraction) → 후보 트리플 `(head, relation, tail)`
4. Entity Resolution → canonical entity ID 매핑
5. Validator (Pydantic schema) → 통과한 것만 적재
6. Neo4j upsert (idempotent: `MERGE`)

이 ingestion 흐름이 GraphRAG의 indexing 단계다.

### Query (read path)
1. User input via Streamlit / MCP / REST
2. Workflow tool dispatcher (Layer 2)
3. Cypher query 또는 GDS 알고리즘 실행
4. Result + provenance(추출 근거 ID) 반환

## Key Design Principles

- **Determinism over flexibility**: 같은 입력에 같은 출력. LLM은 indexing(추출) 단계에만 사용, retrieval과 답변 생성에는 사용하지 않는다. 자연어 layer가 필요한 경우 사용자의 LLM이 우리 MCP 도구를 호출하는 방식으로 처리한다.
- **Provenance everywhere**: 모든 엣지는 출처 ID(공시번호 또는 뉴스 URL)와 추출 시점을 갖는다.
- **Mockable boundary**: 외부 의존성(DART, OpenAI, Neo4j)은 모두 인터페이스 뒤에 둔다.
- **Idempotent ingestion**: 같은 데이터를 두 번 적재해도 그래프 상태가 같다 (`MERGE` only, `CREATE` 금지).

## Module Boundaries

```
src/k_fingraph/
├── sources/        # DART, news fetchers — 외부 호출 격리
├── extract/        # LLM-based NER/RE — mockable
├── resolve/        # Entity Resolution
├── graph/          # Neo4j client, Cypher builders, GDS wrappers
├── workflows/      # Layer 2: 3개 도구 구현
├── interfaces/
│   ├── streamlit_app.py
│   ├── mcp_server.py
│   └── rest_api.py
├── schemas/        # Pydantic models (단일 진실 원천)
└── config.py       # 환경변수 로딩
```

각 모듈은 다른 모듈을 함부로 가로지르지 않는다. 의존 방향은 항상
`interfaces → workflows → graph/extract/resolve → sources/schemas`.
