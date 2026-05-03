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
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Neo4j     │  │  Extraction      │  │  Entity      │ │
│  │  (Aura→    │←─│  Pipeline        │←─│  Resolution  │ │
│  │  Docker)   │  │  (v1+, LLM-based)│  │  (v2+, 텍스트│ │
│  │            │  │                  │  │   임베딩)    │ │
│  └─────┬──────┘  └────────┬─────────┘  └──────────────┘ │
│        │                  ▼                             │
│        │      ┌───────────────────────────────┐         │
│        │      │  Data Sources                 │         │
│        │      │  - DART OpenAPI               │         │
│        │      │  - News (RSS, v1+)            │         │
│        │      └───────────────────────────────┘         │
│        ▼                                                │
│  ┌──────────────────────────┐                           │
│  │  Graph Embedding (v4+)   │  적재 후 별도 batch       │
│  │  GDS 노드 임베딩          │  → find_similar_stocks   │
│  └──────────────────────────┘                           │
└─────────────────────────────────────────────────────────┘
```

> 다이어그램의 노드/엣지 종류는 v0 시점이다. 미래 노드(Person, AuditFirm,
> Event 등)는 아래 **Schema Evolution Timeline** 참조.

## Data Flow

### Ingestion (write path)
1. Source fetch (DART API / news RSS) → `data/raw/`
2. Parser → structured records (Pydantic)
3. LLM extractor (NER + Relation Extraction) → 후보 트리플 `(head, relation, tail)`
   - **v0: skip** — DART 정형 JSON을 그대로 파서 출력으로 사용 (LLM 비활성)
   - **v1+: 활성** — 뉴스·비정형 공시 본문에 LLM NER+RE 적용
4. Entity Resolution → canonical entity ID 매핑
   - **v0: 단순 키 매칭** (ticker / corp_code 직접 비교)
   - **v2+: 텍스트 임베딩 기반 매칭** (상호·임원명 표기 차이 해소)
5. Validator (Pydantic schema) → 통과한 것만 적재
6. Neo4j upsert (idempotent: `MERGE`)

이 ingestion 흐름이 GraphRAG의 indexing 단계다.

### Embedding Pipelines

본 시스템에는 두 종류의 임베딩이 등장한다. 둘은 단계·목적·시점이 다르므로
구분해서 다룬다.

| 종류 | 도입 시점 | 위치 | 목적 |
|---|---|---|---|
| 텍스트 임베딩 | v2 | Ingestion 4번 (Entity Resolution) 내부 | 상호·임원명의 표기 차이를 임베딩 유사도로 해소하여 동일 엔티티로 병합 |
| 그래프 임베딩 | v4 | 적재 완료된 Neo4j 위에서 별도 batch (GDS) | 노드 간 구조적 유사도 계산 → `find_similar_stocks`의 retrieval 신호 |

그래프 임베딩은 ingestion 안에 있지 않다 — 그래프가 일정 규모로 채워진
뒤 주기적으로 재계산되는 별도 파이프라인이며, retrieval 시점에 캐시에서
조회된다.

### Query (read path)
1. User input via Streamlit / MCP / REST
2. Workflow tool dispatcher (Layer 2)
3. Cypher query 또는 GDS 알고리즘 실행
4. Result + provenance(추출 근거 ID) 반환

## Key Design Principles

- **Determinism over flexibility**: 같은 입력에 같은 출력. LLM은 v1부터 indexing(추출) 단계에만 사용하며 (v0는 DART 정형 JSON으로 LLM 없이 적재), retrieval과 답변 생성에는 사용하지 않는다. 자연어 layer가 필요한 경우 사용자의 LLM이 우리 MCP 도구를 호출하는 방식으로 처리한다.
- **Provenance everywhere**: 모든 엣지는 출처 ID(공시번호 또는 뉴스 URL)와 추출 시점을 갖는다.
- **Mockable boundary**: 외부 의존성(DART, OpenAI, Neo4j)은 모두 인터페이스 뒤에 둔다.
- **Idempotent ingestion**: 같은 데이터를 두 번 적재해도 그래프 상태가 같다 (`MERGE` only, `CREATE` 금지).

## Schema Evolution Timeline

그래프 schema는 한 번에 모든 노드/엣지 타입을 채우지 않는다. 각 sprint
진입 시점에 그 sprint의 KPI 달성에 필요한 신호만 ADR로 결정한 뒤 추가한다.
근거와 절차는 [ADR 0005](decisions/0005-v0-schema-scope.md).

| 시점 | 추가 노드 | 추가 엣지 | 트리거 (sprint KPI) |
|---|---|---|---|
| v0 (now) | `Company` | `OWNS` | KOSPI 200 + 지분 그래프 + Cypher 3개 + Streamlit |
| v1 | `Event` | `MENTIONED_IN` 등 | 뉴스 추출 파이프라인 가동 (LLM NER+RE 활성) |
| v3 | `Person` | `EXECUTIVE_OF` | 충격 전파 시뮬레이션의 임원 겸직·지배구조 신호 |
| v4 | `AuditFirm` 등 | `AUDITED_BY` 등 | 유사 종목 발굴의 감사·재무 신호 (정확한 신호는 v4 KPI 정의 후 확정) |
| v5 | (대체로 재활용) | (대체로 재활용) | 포트폴리오 리스크 — 기존 노드 조합으로 충분할 가능성 높음 |

각 행의 노드/엣지 타입은 **확정이 아니라 현재 시점의 가설**이다. v3·v4·v5
진입 시점에 [`docs/data-notes.md`](data-notes.md)의 "향후 v3·v4·v5 진입 시
추가 학습 필요 API 카탈로그" 섹션을 근거로 정확한 신호를 다시 식별하고,
신규 ADR로 명시한 뒤 `docs/schema.md`를 갱신한다. v0 시점에 이 표를 보고
선제적으로 schema를 확장하지 않는다.

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
