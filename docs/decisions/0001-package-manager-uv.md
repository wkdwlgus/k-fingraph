# ADR 0001: Package Manager는 uv를 사용한다

- Status: Accepted
- Date: 2026-04-27

## Context

Python 의존성 관리 도구 선택. 후보:
- pip + venv (전통)
- poetry (lock 파일, 의존성 해결)
- pdm (PEP 582)
- uv (Rust 기반, Astral)

## Decision

**uv를 사용한다.**

## Rationale

- 의존성 해결과 설치가 다른 도구 대비 10~100배 빠름 → 빠른 피드백 루프 보장
- `pyproject.toml` + `uv.lock` 구조가 표준 (PEP 621)
- `uv run`으로 가상환경 활성화 없이 명령 실행 가능 → Claude Code의 bash 자동화에 유리
- 단일 바이너리, Python 인터프리터 관리도 통합 (`uv python install`)

## Consequences

- 팀 합류 시 uv 설치만 안내하면 됨
- pip/poetry 명령어 사용 금지 — `CLAUDE.md`의 Non-Negotiables에 명시
- 외부 라이브러리가 poetry 전제로 문서화된 경우 변환 필요 (실제로는 `pyproject.toml` 호환)

## Supersedes / Superseded by

- 없음
