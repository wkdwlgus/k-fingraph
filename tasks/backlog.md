# Backlog

> 미래 작업 풀. 우선순위 매기지 않음 (스프린트 시작 시 `current.md`로 이동).

## v1: 뉴스 추출 파이프라인 (GraphRAG indexing)
- 뉴스 RSS 수집 (한경, 매경 등)
- LLM 기반 NER + Relation Extraction
- Pydantic 검증 → Neo4j 적재
- 추출 품질 평가셋 만들기

## v2: Entity Resolution
- 1차: string normalization + corp_code 매칭
- 2차: 임베딩 유사도 (BGE-M3 또는 KoSimCSE)
- 3차: LLM judge 결합
- 평가셋: 동명이인/유사회사명 50쌍 라벨링

## v3: 충격 시뮬레이터 (도구 1, GraphRAG retrieval)
- BFS/DFS 기반 propagation 알고리즘
- 엣지 가중치 기반 점수 감쇠
- Streamlit 워크벤치 통합
- 평가: 과거 위기 사건 백테스트

## v4: 유사 종목 (도구 2, GraphRAG retrieval)
- Node2Vec 임베딩
- (선택) GraphSAGE 비교
- 평가: KOSPI 종목별 주가 상관계수 상위 N개와 비교

## v5: 포트폴리오 리스크 (도구 3, GraphRAG retrieval)
- Centrality 계산
- Community Detection (Louvain)
- 시나리오별 노출도 점수

## v6: MCP 서버 (GraphRAG 도구를 LLM에 노출)
- 3개 도구를 MCP tool로 노출
- Claude Desktop 연결 검증 (실제 LLM이 도구를 호출해 의미있는 응답을 생성하는지)

## v7: 평가 리포트
- GraphRAG vs Vector RAG 30~50문항 비교
- 결과를 `docs/evaluation/` 아래에 정리

## 잡일 풀
- 로깅 표준화
- API 응답 스키마 OpenAPI 스펙 문서화
- Dockerfile + docker-compose
- GitHub Actions CI
