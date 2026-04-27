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
