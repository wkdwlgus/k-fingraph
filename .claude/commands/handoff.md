# /handoff — 세션 종료 전 문서 동기화

다음을 순차 실행하라:

1. **`tasks/current.md` 업데이트**
   - 이번 세션에서 완료한 항목에 [x] 체크
   - 막힌 항목이 있으면 `Blocked / Questions` 섹션에 명시
   - 다음 세션이 바로 이어갈 수 있도록 in-progress 표기

2. **`docs/progress.md`에 로그 추가**
   ```
   ## YYYY-MM-DD
   - 한 줄 요약: 무엇을 했나
   - (선택) 다음 세션이 알아야 할 컨텍스트
   ```

3. **새 결정이 있었다면 ADR 작성**
   - `docs/decisions/000N-{topic}.md` 생성
   - Context / Decision / Rationale / Consequences 섹션 채움

4. **트러블슈팅 사례가 있었다면 기록**
   - `docs/troubleshooting.md`에 증상/원인/해결/교훈 형식으로 추가
   - 재발 방지를 위한 anti-pattern을 `CLAUDE.md`에 한 줄로 추가

5. **변경된 파일 리스트를 사용자에게 제시**
   - `git status` 실행 결과 보여주기
   - 커밋은 사용자가 직접 (메시지 제안은 가능)

6. 모든 작업 완료 후 한 줄 요약: "이번 세션에서 X 완료. 다음 세션은 Y부터."
