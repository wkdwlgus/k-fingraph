# ADR 0004: GraphRAG를 명시적 프레임으로 채택한다

- Status: Accepted
- Date: 2026-04-28

## Context

초기 설계에서 "챗봇 아님" 결정을 내리면서 GraphRAG를 명시적 프레임으로
두지 않았다. 자연어 입력 → LLM 답변 생성 흐름을 시스템 안에 두지 않기로
한 것이 GraphRAG 자체를 부정하는 것처럼 묶여서 정리되어 있었다.

재검토 결과, 챗봇 여부와 GraphRAG 채택은 별개 이슈임을 확인했다.
우리 시스템의 indexing(LLM 기반 비정형 텍스트 추출)과
retrieval(그래프 위 multi-hop traversal)은 이미 GraphRAG 패턴 그 자체이며,
단지 자연어 layer를 우리 서버 안에 두지 않았을 뿐이다.

## Decision

**GraphRAG를 indexing(v1) + retrieval(v3~v5) + tool exposure(v6) +
평가(v7) 전 영역에 명시적 프레임으로 채택한다.**

단, 사용자에게 노출되는 인터페이스는 챗봇이 아닌 워크벤치 / MCP 도구
호출 방식을 유지한다. 자연어 답변 생성을 우리 서버 안에서 수행하지
않는다는 결정(ADR 0001~0003 기조)은 그대로다.

## Rationale

- **이름을 정확하게 붙이는 것이 정직한 포지셔닝이다.** 도구 3개의
  본질이 이미 graph 위 multi-hop retrieval이며, 비정형 텍스트(DART
  공시, 뉴스)에서 LLM으로 그래프를 구축하는 v1은 GraphRAG의 indexing
  단계 그 자체다. 다른 이름으로 부르는 것은 부정확하다.

- **책임 경계가 명확해진다.** GraphRAG는 Cypher/GDS의 superset이며,
  우리는 그중 indexing(LLM 추출)과 retrieval(Cypher/GDS 도구)을 직접
  구현하고, 자연어 layer는 사용자의 LLM(Claude/ChatGPT 등)에 위임한다.
  결정론적 부분만 우리가 책임지고, 자연어 답변 품질은 호출자 LLM의
  책임이 된다.

- **"GraphRAG 패턴을 따르는 시스템"으로 포지셔닝하며 Microsoft
  GraphRAG 구현체와는 별개임을 명시한다.** 우리는 한국 금융 도메인에
  특화된 자체 구현이며, 특정 GraphRAG 라이브러리에 의존하지 않는다.

## Consequences

- `docs/architecture.md`: Layer 2 설명에 "GraphRAG retrieval" 표기 추가,
  Ingestion 섹션 끝에 "GraphRAG indexing 단계" 명시, Key Design
  Principles의 LLM 사용 범위 문구 갱신.
- `tasks/backlog.md`: v1, v3, v4, v5, v6 제목에 GraphRAG 단계 표기 추가.
- 코드 변경 없음. 모듈 경계와 함수 시그니처는 그대로 유효하다.
- v7 평가(GraphRAG vs Vector RAG)의 의미가 더 또렷해진다 — "우리가
  선택한 패턴이 도메인 질문에서 우월한지"를 묻는 것이 된다.

## Supersedes / Superseded by

- 없음. ADR 0001~0003의 결정을 변경하지 않으며, 포지셔닝 명시만 보완.
