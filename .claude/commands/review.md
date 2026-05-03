# /review — 변경사항 자가 리뷰

방금까지 작업한 내용에 대해 다음을 점검하라:

1. **`conventions.md` 및 CLAUDE.md Non-Negotiables·Anti-Patterns 위반 여부**
   — type hint, bare except, print, 한국어 식별자, 외부 호출 도메인 예외
   변환, 비밀값 로그 노출 등

2. **CLAUDE.md "Feedback Loops" 4개 명령 모두 실행** — 결과 보고

3. **schema.md 변경 필요 여부** — 새 노드/엣지 타입 추가됐다면 ADR 작성 확인

4. **테스트 커버리지** — 새 함수 단위 테스트 + 외부 의존성 모킹

5. 위 4개 중 하나라도 실패 시, **수정 제안만 제시**하고 사용자 승인 후 수정.
