# ADR 0002: Neo4j는 Aura Free로 시작, 한계 도달 시 Docker로 전환

- Status: Accepted
- Date: 2026-04-27

## Context

그래프 DB 호스팅 전략. 후보:
- Neo4j Aura Free: 클라우드 매니지드, 무료, 노드 200k / 관계 400k 제한
- Neo4j Aura Pro: 유료
- Docker 로컬 (Community Edition): 무료, 무제한, 셋업 ~30분
- Docker 로컬 (Enterprise Trial): GDS 고급 기능 포함, 30일 제한

## Decision

**v0~v3까지는 Aura Free로, 다음 트리거 중 하나라도 발생 시 Docker로 전환한다.**

전환 트리거:
1. 노드 수가 150k에 도달 (200k 한도의 75%)
2. 관계 수가 300k에 도달 (400k 한도의 75%)
3. GDS의 Aura Free에서 미지원 알고리즘이 필요해짐 (예: 일부 GraphSAGE)
4. 쿼리 latency가 일관되게 5초 초과

전환 방식:
- `docker-compose.yml` 추가
- 같은 Neo4j 버전 사용 (호환성)
- `cypher-shell` 또는 `apoc.export`로 Aura → Docker 데이터 마이그레이션
- 환경변수 `NEO4J_URI`만 변경하여 코드 변경 없이 전환

## Rationale

- v0~v3는 KOSPI 200 + 일부 관계 → 노드 수천 단위, Aura Free로 충분
- 셋업 시간 0분으로 즉시 시작 가능
- 무료 → 비용 부담 없음
- 호스팅 방식 결정을 도메인 요구(데이터 규모, GDS 알고리즘 가용성, latency)로 묶어두어 추후 재논의 시 근거가 명확함

## Consequences

- 코드는 처음부터 환경변수 기반 연결 설정 (전환 비용 최소화)
- 백업: Aura Free는 자동 백업 없음 → 주 1회 수동 dump 스크립트 필요 (v1 이후)

## Supersedes / Superseded by

- 없음
