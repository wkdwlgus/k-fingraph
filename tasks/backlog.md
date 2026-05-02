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

## v8: Operational Pipeline (정기 ingestion·운영 자동화)
- 데이터 종류별 갱신 cadence 정의
  - corpCode.xml: 일 1회
  - 정기 사업보고서: 분기 마감(3·5·8·11월) 직후
  - 주요사항보고서·지분공시: 거의 실시간 (DART webhook 또는 짧은 polling)
  - 뉴스 RSS (v1 이후): 시간 단위
- 스케줄러 도입: 가장 가벼운 것부터 (GitHub Actions cron → 필요 시 Prefect/Airflow)
- 적재 실패 알림 + 재시도 정책
- 데이터 freshness 메트릭 (소스별 마지막 적재 시각 추적)
- 비고: v0~v5는 수동 트리거(`fetch_corp_codes()` 등 순수 함수 직접 호출)로 진행.
  도구·그래프 품질이 검증된 뒤에야 자동화 비용이 정당화되므로 의식적으로 지연.

## 잡일 풀
- 로깅 표준화
- API 응답 스키마 OpenAPI 스펙 문서화
- Dockerfile + docker-compose
- GitHub Actions CI
- 유니버스 확장: KOSPI 200 → 전체 KOSPI(~900) + KOSDAQ(~1500) 적재.
  적재 성능·시각화 부담 검증 필요. 시점 종속이 없어 어느 단계에서든 진입 가능.
