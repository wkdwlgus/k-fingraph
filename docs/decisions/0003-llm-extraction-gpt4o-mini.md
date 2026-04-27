# ADR 0003: LLM 추출은 GPT-4o-mini만 사용한다

- Status: Accepted
- Date: 2026-04-27

## Context

NER + Relation Extraction에 사용할 LLM 선택. 후보:
- GPT-4o-mini (OpenAI API)
- Claude 3.5 Haiku (Anthropic API)
- Qwen2.5-7B-Instruct (자체 호스팅, RunPod 또는 로컬)
- 한국어 특화 모델 (HyperCLOVA X 등)

## Decision

**GPT-4o-mini를 사용한다. 모델 비교 실험은 본 프로젝트의 scope 외다.**

## Rationale

- 단일 모델로 시작 → 추출 품질 변동 요인을 줄여 디버깅 단순화
- GPT-4o-mini는 한국어 성능이 충분하고 비용이 매우 저렴 (1M 토큰 기준 $0.15 input / $0.60 output)
- API 호출이라 인프라 부담 없음 → MVP 속도 우선
- 자체 호스팅(Qwen)은 cold start, 추론 latency, GPU 비용 등 별도 변수 — 핵심 작업이 흐려진다
- 본 프로젝트의 가치 명제는 "그래프 기반 결정론적 추론"이지 "LLM 모델 비교"가 아니다

## Trade-offs

- 데이터가 외부로 나감 → 민감 정보 없는 공개 데이터(DART, 뉴스)만 다루므로 허용
- API 의존성 → mockable interface로 격리하여 테스트 영향 최소화

## When to Revisit

- 데이터에 민감 정보 포함 필요 시
- API 비용이 월 $50 초과 시
- 추출 품질이 명확히 부족하다는 증거가 production에서 발견될 시

LLM 모델 성능 비교 자체는 본 프로젝트의 scope가 아니다.
GraphRAG vs Vector RAG 비교(v7)는 retrieval 시스템 비교이지 모델 성능 비교가 아니다.

## Supersedes / Superseded by

- 없음
