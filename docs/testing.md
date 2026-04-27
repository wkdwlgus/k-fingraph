# Testing Strategy

## Three Tiers

| Tier | Mark | 목적 | 외부 의존성 | 실행 빈도 |
|---|---|---|---|---|
| Unit | `@pytest.mark.unit` | 로직 검증 | 전부 mock | 매 변경 |
| Integration | `@pytest.mark.integration` | 모듈 간 통합 | testcontainers Neo4j | 매 PR |
| E2E | `@pytest.mark.e2e` | 실제 외부 API 동작 확인 | DART/OpenAI 실호출 | 1일 1회 |

## Default Command (CI / pre-commit)

```bash
uv run pytest -m "not e2e"
```

E2E는 로컬에서 의도적으로만 실행:

```bash
uv run pytest -m e2e
```

## Mock vs Real — 결정 규칙

### 항상 Mock해야 하는 것

- **OpenAI API 호출** — 비용, 비결정성, latency
- **DART API 호출** — rate limit, 외부 장애에 영향받지 않게
- **시간** — `datetime.now()` 의존 로직은 `freezegun` 또는 `monkeypatch`
- **랜덤** — seed 고정

### Mock하지 말아야 하는 것

- **Pydantic 검증** — 진짜 데이터로 깨지는지 봐야 의미가 있음
- **Cypher 쿼리** — testcontainers Neo4j 사용 (integration tier)
- **파싱 로직** — 실제 fixture 파일 기반 테스트

### 회색 지대: 직접 호출과 모킹의 하이브리드

**Record-Replay 패턴**을 사용한다.

1. 최초 1회만 실제 호출 → 응답을 `tests/fixtures/`에 저장
2. 이후 테스트는 fixture를 읽어 모킹된 응답으로 재생
3. fixture는 git에 커밋 (외부 데이터 의존성을 코드 안으로 가져옴)
4. fixture를 갱신해야 할 때만 `--record` 플래그로 재호출

구현은 `httpx-vcr` 또는 자체 작성한 fixture loader. v0에서는 자체 작성으로 시작 (단순):

```python
# tests/conftest.py
from pathlib import Path
import json

FIXTURES = Path(__file__).parent / "fixtures"

def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())
```

## E2E 실행 정책

- 로컬: 작업 마무리 시점에 1회 (`uv run pytest -m e2e`)
- CI: 매일 UTC 02:00 (cron) — 외부 API 깨졌는지 모니터링용
- PR: 실행 안 함 (비용 + 느림)

## 어떤 테스트를 어디에 두는가

```
tests/
├── unit/
│   ├── test_parsers.py        # DART 응답 파싱 (mocked)
│   ├── test_extract.py        # LLM 추출 로직 (mocked)
│   ├── test_resolve.py        # Entity Resolution (pure logic)
│   └── test_workflows.py      # 워크플로우 함수 (mocked graph)
├── integration/
│   ├── test_graph_client.py   # Neo4j testcontainer
│   └── test_ingest.py         # 파이프라인 통합
├── e2e/
│   ├── test_dart_e2e.py       # 실제 DART 호출
│   └── test_openai_e2e.py     # 실제 OpenAI 호출
└── fixtures/
    ├── dart/
    │   ├── corp_code.xml
    │   ├── samsung_report.json
    │   └── lg_report.json
    ├── openai/
    │   └── ner_responses.json
    └── kospi200.csv
```

## Coverage 목표

- v0: src/ 전체 60% 이상
- v3: 75% 이상
- 100%는 목표 아님 — 의미 있는 테스트가 우선

## 외부 의존성 추가 시 체크리스트

새로운 외부 API/서비스를 추가할 때:

1. [ ] 인터페이스(추상 클래스 또는 Protocol) 먼저 정의
2. [ ] 실제 구현은 인터페이스 뒤에 격리
3. [ ] Mock 구현 추가 (`tests/fakes/`)
4. [ ] Fixture 파일 1~2개 저장
5. [ ] e2e 핑 테스트 추가
6. [ ] `CLAUDE.md`의 Non-Negotiables에 새 API key 추가
7. [ ] `docs/setup.md`의 외부 계정 발급 섹션에 안내 추가
