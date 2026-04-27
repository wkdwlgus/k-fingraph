# /review — 변경사항 자가 리뷰

방금까지 작업한 내용에 대해 다음을 점검하라:

1. **`docs/conventions.md` 위반 없는가**
   - type hint 누락된 public 함수
   - bare except
   - print 사용
   - 한국어 식별자

2. **피드백 루프 통과**
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/`
   - `uv run pytest -m "not e2e"`
   각각 실행하고 결과 보고

3. **schema.md 변경 필요 여부**
   - 새 노드/엣지 타입이 추가되었나?
   - 추가됐다면 ADR이 작성되었나?

4. **테스트 커버리지**
   - 새 함수에 단위 테스트가 있는가?
   - 외부 의존성은 모킹되었는가?

5. **CLAUDE.md anti-patterns 위반 여부**

6. 위 5개 중 하나라도 실패 시, **수정 제안만 제시**하고 사용자 승인 후 수정.
