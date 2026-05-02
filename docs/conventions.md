# Code Conventions

## Tooling

- **Python**: 3.12
- **Package manager**: uv (only)
- **Lint**: ruff (replaces flake8/black/isort)
- **Type check**: mypy with `strict = true` for `src/`
- **Test**: pytest + pytest-mock

## Naming

- 함수/변수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 한국어 식별자 금지 (DB 값으로는 OK, 코드 식별자는 영어)
- 모듈명은 단수형: `extract`, not `extractors`

## Type Hints

- Public 함수 100% 필수
- 내부 함수도 권장
- `Any` 사용 시 `# type: ignore[explanation]` 코멘트 필수

## Error Handling

- 외부 호출(DART, OpenAI, Neo4j)은 항상 try/except로 감싸고, 도메인 예외로 변환:
  - `DartAPIError`, `LLMExtractionError`, `GraphWriteError` 등
- 도메인 예외는 `src/k_fingraph/errors.py`에 정의
- `bare except:` 금지

## Logging

- `logging` 모듈 사용 (print 금지)
- 모듈별 logger: `logger = logging.getLogger(__name__)`
- 외부 호출 시 INFO 레벨로 입력/출력 요약 기록
- 비밀값(API key)은 로그에 절대 포함 금지

## Testing Policy

→ `docs/testing.md` 참조

요약:
- Unit test: 외부 의존성 모두 mock, 빠르고 결정론적
- Integration test: Neo4j는 testcontainers 사용
- E2E test: 실제 DART/OpenAI 호출, `@pytest.mark.e2e`, CI에서는 일정 주기로만

## Git

- 브랜치: `main` / `feat/*` / `fix/*` / `docs/*`
- 커밋 메시지: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
- PR 머지 전 체크: ruff + mypy + pytest 모두 통과

### 커밋 메시지 작성 규칙

**원칙**: 이 저장소를 처음 보는 외부 개발자가 메시지만 읽고도 무엇이
바뀌었는지 이해할 수 있어야 한다.

- 내부 용어·약어 금지:
  - ❌ `Day 1`, `Day 2` 등 스프린트 일자 표기 — 외부에서는 의미 없음
  - ❌ `current.md`, `progress.md`, `backlog.md` 같은 파일명만 노출
    — 그 파일이 무엇인지 모름
  - ❌ `v0`, `MVP-zero` 같은 내부 마일스톤 코드 (PR/태그에서는 OK,
    커밋 본문에서는 의미 풀어쓰기)
- 무엇이 바뀌었는지를 도메인 용어로 풀어쓴다:
  - ✅ `docs: 환경 셋업 진행 상황 및 남은 외부 의존성 기록`
  - ✅ `docs: 스프린트 작업 목록 체크 처리 및 외부 키 발급 블로커 명시`
- 파일명을 적어야 할 때는 그 파일의 역할도 함께:
  - ❌ `docs: progress.md 업데이트`
  - ✅ `docs: 작업 로그(progress.md)에 환경 셋업 완료 항목 추가`
- 제목은 50자 이내, 본문이 필요하면 한 줄 띄우고 풀어쓴다.

## File Organization

- 한 파일 한 책임. 500줄 넘으면 분할 검토.
- `__init__.py`는 비워두거나 명시적 re-export만.
- 테스트는 `tests/`에서 `src/` 구조 미러링.

## Documentation in Code

- 모듈 docstring: 무엇을 하는지 1~3줄
- 클래스/공개 함수 docstring: Google 스타일
- 인라인 코멘트는 "왜"를 설명, "무엇"은 코드로 표현

## Schema Changes

`docs/schema.md` 변경은 ADR 필수. 코드보다 스키마 문서가 먼저.

## 외부 도구·모델 선택 ADR 4단계

외부 라이브러리·모델·인프라(임베딩 모델, 그래프 알고리즘 라이브러리, 스케줄러,
평가 프레임워크, MCP·LLM SDK 등) 선택은 다음 4단계를 거친 ADR로 박는다.
**후보를 사전에 박지 않는다 — 후보는 단계 2에서 수집한다.**

1. **평가 기준 정의 (먼저)** — 그 도구가 충족해야 할 정량·정성 기준을 명문화한다.
   예: 한국어 회사명 매칭 recall@k, 인퍼런스 latency, 메모리, 라이선스 제약,
   운영 난이도. 기준은 그 도구가 들어가는 sprint의 KPI에서 역산한다.
2. **후보 survey (그 시점에)** — 단계 1의 기준을 만족할 만한 후보들을 그 시점의
   생태계에서 모은다. 백로그·이전 ADR에 박혀 있던 후보는 stale일 가능성이 높으므로
   참고만 하고 새로 조사한다.
3. **정량 비교** — 단계 1의 평가 기준대로 후보들을 측정한다. 측정 결과는 ADR의
   `Rationale`에 표 형태로 포함한다 (어느 후보가 어느 지표에서 얼마였는지).
4. **결정 + Rationale** — 측정 결과 + trade-off 설명 + 왜 그 후보를 택했는지를
   명시한다. 측정 데이터가 없는 정성 평가도 명시 (예: "라이선스 제약으로 후보 X를
   제외").

### 안티패턴

- ❌ 백로그·plan에 후보 모델·라이브러리 이름을 미리 박아두는 것 (예전 인기 모델이
  지금도 최선이라고 가정하게 됨)
- ❌ "흔히 쓰이니까" 또는 "예전 프로젝트에서 썼으니까"를 ADR Rationale로 사용
- ❌ 평가 기준 없이 도구를 먼저 정해두고 사후 정당화

### 예외

- 표준 라이브러리(stdlib·널리 쓰이는 framework의 official SDK 등)는 ADR 불요.
  예: Pydantic, ruff, mypy, httpx, Anthropic 공식 MCP SDK.
- 본 원칙은 **선택 여지가 있고 우리 산출물 품질에 영향을 주는** 외부 의존성에만
  적용된다.
