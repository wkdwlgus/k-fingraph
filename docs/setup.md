# Setup Guide

> 처음 환경을 셋업하거나 새 환경(다른 머신, 새 팀원)에서 시작할 때 이 문서를 따른다.

## Prerequisites (사람이 직접 해야 하는 부분)

### 1. 외부 계정 및 키 발급

- **Neo4j Aura Free**: https://neo4j.com/cloud/aura-free/
  - 인스턴스 생성 시 받는 정보 (모두 필요):
    - Connection URI (예: `neo4j+s://xxxxx.databases.neo4j.io`)
    - Username (기본값: `neo4j`)
    - Generated password (인스턴스 생성 시 1회만 표시 — 반드시 저장)
- **DART OpenAPI**: https://opendart.fss.or.kr/
  - 회원가입 후 인증키 신청 (즉시 발급, 무료)
- **OpenAI API**: https://platform.openai.com/
  - API key 생성 후 결제수단 등록 (`sk-` 로 시작)

### 2. 로컬 도구 설치

```bash
# uv (Python 패키지 매니저)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Claude Code CLI (이미 설치되어 있다면 skip)
# https://docs.claude.com/en/docs/claude-code/quickstart 참조

# git (당연히 필요)
```

## Environment Variables

`.env` 파일은 **로컬에만 존재하며 절대 커밋되지 않는다**. `.env.example`이 템플릿이다.

### .env.example (커밋됨, 템플릿)

```bash
# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# DART OpenAPI
DART_API_KEY=

# OpenAI
OPENAI_API_KEY=

# Logging
LOG_LEVEL=INFO
```

### .env 만들기 (커밋되지 않음, 실제 값)

```bash
cp .env.example .env
# 그 다음 에디터로 .env 열어서 위에서 발급받은 실제 값을 채운다
```

### 주의사항

- `.env` 파일은 `.gitignore`에 포함되어 있어야 한다 (반드시 확인)
- API key를 채팅, 슬랙, 이슈 등 어디에도 붙여넣지 말 것
- 실수로 커밋했다면 즉시 키를 발급기관에서 무효화하고 새로 발급
- LLM(Claude Code 포함)에게 .env 내용을 직접 보여주지 말 것 — 필요시 변수명만 언급

## First Run Verification

환경 셋업이 끝나면 다음 순서로 검증한다.

```bash
# 1. 의존성 설치
uv sync --all-extras

# 2. 코드 품질 검증
uv run ruff check .
uv run mypy src/

# 3. 단위 테스트 (외부 API 호출 없음)
uv run pytest -m unit

# 4. E2E 핑 테스트 (실제 외부 API 호출, 비용 약 $0.001)
uv run pytest -m e2e
```

`pytest -m e2e`까지 통과하면 Neo4j Aura, DART, OpenAI 모두 살아있다는 뜻.

## Troubleshooting Setup

### Neo4j Aura 연결 실패

- URI가 `neo4j+s://` 로 시작하는지 (보안 연결) 확인
- 비밀번호 특수문자 issue: `.env`에서 따옴표 없이 그대로 입력
- 무료 인스턴스는 일정 시간 미사용 시 일시 정지 → Aura console에서 resume

### DART API 호출 실패

- 인증키 발급 직후 활성화까지 수 분 소요 가능
- `status: "010"` 응답: 키 등록 안 됨
- `status: "020"` 응답: 호출 한도 초과 (일 10,000건)

### OpenAI 인증 실패

- 결제수단 등록 안 되어 있으면 401
- 조직(org) 설정이 필요한 경우 .env에 `OPENAI_ORG_ID` 추가 검토

## Adding New Environment Variables

새 외부 의존성을 추가할 때:

1. `.env.example`에 변수명 추가 (값은 비워두기)
2. `src/k_fingraph/config.py`의 `Settings` 클래스에 필드 추가
3. `tests/test_smoke.py`에 핑 테스트 추가
4. 본 문서(setup.md)의 "외부 계정 및 키 발급" 섹션에 발급 안내 추가
5. `CLAUDE.md`의 Non-Negotiables에 키 보호 사항 명시 (필요시)
