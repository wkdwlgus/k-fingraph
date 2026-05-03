# Backlog

> 미래 작업 풀. 우선순위 매기지 않음 (스프린트 시작 시 `current.md`로 이동).

## v1: 뉴스 추출 파이프라인 (GraphRAG indexing)
- 뉴스 RSS 수집 (한경, 매경 등)
- LLM 기반 NER + Relation Extraction
- Pydantic 검증 → Neo4j 적재
- 추출 품질 평가셋 만들기

## v2: Entity Resolution
- 1차: string normalization + corp_code 매칭
- 2차: 텍스트 임베딩 유사도 — 모델은 v2 진입 시점 ADR로 결정
- 3차: LLM judge 결합
- 평가셋: 동명이인/유사회사명 50쌍 라벨링
- 진입 전 ADR 작성: 텍스트 임베딩 모델 선택
  - `docs/conventions.md`의 "외부 도구 선택 ADR 4단계" 원칙을 따름
  - 평가 기준: 한국어 회사명 매칭 recall@k, 인퍼런스 latency, 메모리·디스크,
    라이선스
  - 후보 모델 survey는 v2 진입 시점에 다시 수행 (한국어 임베딩 생태계 변화
    빠름 — 지금 후보를 박지 않는다)
  - 위 평가셋(50쌍 라벨링)으로 정량 비교한 결과를 ADR Rationale에 명시
    (어느 모델이 어느 지표에서 얼마나 우월했는지, 어떤 trade-off로 결정했는지)

## v3: 충격 시뮬레이터 (도구 1, GraphRAG retrieval)
- BFS/DFS 기반 propagation 알고리즘
- 엣지 가중치 기반 점수 감쇠
- Streamlit 워크벤치 통합
- 평가: 과거 위기 사건 백테스트
- 진입 전 결정 재검토: **OWNS `relation_type` 임계값 (ADR 0006)**
  - v0에서 단순 % 휴리스틱(50/20/0)으로 박혔음. 충격 전파 정확도가 분류에
    민감한지 백테스트로 측정.
  - 검토 항목: (a) `invstmnt_purps`("경영참여"/"단순투자") 텍스트 정규화로
    분류 정확도 향상 여부, (b) 임계값 조정, (c) 새 enum 값(`PARTICIPATING`/
    `PASSIVE`) 도입 여부.
  - 변경 결정 시 ADR 0006을 supersede하는 신규 ADR 작성.

## v4: 유사 종목 (도구 2, GraphRAG retrieval)
- 그래프 임베딩 적용 — 알고리즘·라이브러리는 v4 진입 시점 ADR로 결정
- 평가: KOSPI 종목별 주가 상관계수 상위 N개와 비교
- 진입 전 ADR 작성: 그래프 임베딩 알고리즘 + 라이브러리 (Neo4j GDS vs 별도)
  - `docs/conventions.md`의 "외부 도구 선택 ADR 4단계" 원칙을 따름
  - 평가 기준: 주가 상관계수와의 일치도, 그래프 규모 처리 가능성, GDS
    Community 라이선스 제약, 추론 latency
  - 후보 알고리즘 survey는 v4 진입 시점에 수행 (그 시점 SOTA가 무엇인지에
    따라 달라짐 — 지금 후보를 박지 않는다)
  - 정량 비교 결과를 ADR Rationale에 명시

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
- 스케줄러 도입 — 라이브러리·인프라는 v8 진입 시점 ADR로 결정
- 적재 실패 알림 + 재시도 정책
- 데이터 freshness 메트릭 (소스별 마지막 적재 시각 추적)
- 진입 전 ADR 작성: 스케줄러 선택 (GitHub Actions cron / Prefect / Airflow / 기타)
  - `docs/conventions.md`의 "외부 도구 선택 ADR 4단계" 원칙을 따름
  - 평가 기준: 운영 난이도, 모니터링·재시도 기능, 비용, 그 시점 우리 스택과의
    적합성
- 비고: v0~v5는 수동 트리거(`fetch_corp_codes()` 등 순수 함수 직접 호출)로 진행.
  도구·그래프 품질이 검증된 뒤에야 자동화 비용이 정당화되므로 의식적으로 지연.

## 잡일 풀
- 로깅 표준화
- API 응답 스키마 OpenAPI 스펙 문서화
- Dockerfile + docker-compose
- GitHub Actions CI
- 유니버스 확장: KOSPI 200 → 전체 KOSPI(~900) + KOSDAQ(~1500) 적재.
  적재 성능·시각화 부담 검증 필요. 시점 종속이 없어 어느 단계에서든 진입 가능.
