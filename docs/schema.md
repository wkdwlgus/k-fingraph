# Graph Schema (v0)

> ⚠️ 이 문서는 살아있는 문서다. 노드/엣지 타입 변경 시 반드시 ADR을 먼저 작성한다.

## Versioning

- **v0** (current): KOSPI 200 기업 + 지분 관계만. DART 데이터로 한정.
- v1 (planned): 인물(임원·대주주) 노드 추가, 뉴스 기반 이벤트 노드 추가.
- v2 (planned): 산업/제품 분류 노드, 공급/경쟁 관계 추가.

## Node Types (v0)

### `Company`
한국 상장 기업.

| Property | Type | Required | Note |
|---|---|---|---|
| `ticker` | string | ✅ | KRX 종목코드, primary identifier |
| `corp_code` | string | ✅ | DART 고유번호 (8자리) |
| `name_kr` | string | ✅ | 정식 한글 상호명 |
| `name_normalized` | string | ✅ | 정규화 (공백·"(주)"·"주식회사" 제거) |
| `name_en` | string | optional | 영문명 |
| `market` | enum | ✅ | KOSPI / KOSDAQ / KONEX |
| `industry_krx` | string | optional | KRX 산업분류 |
| `created_at` | datetime | ✅ | 노드 생성 시점 |
| `updated_at` | datetime | ✅ | 마지막 갱신 시점 |

**Constraint**: `ticker` UNIQUE, `corp_code` UNIQUE.

## Edge Types (v0)

### `OWNS`
A가 B의 지분을 보유한 관계.

| Property | Type | Required | Note |
|---|---|---|---|
| `stake_pct` | float | ✅ | 지분율 (0~100) |
| `relation_type` | enum | ✅ | SUBSIDIARY / AFFILIATE / OTHER |
| `as_of` | date | ✅ | 공시 기준일 |
| `source_id` | string | ✅ | DART 공시번호 (rcept_no) |
| `extracted_at` | datetime | ✅ | 추출 시점 |

**Cardinality**: A→B 다중 가능 (시점별로 별도 엣지). 최신은 `as_of` desc 1개로 조회.

## Provenance Convention

모든 엣지는 `source_id` + `extracted_at` 필수. 출처 없는 엣지는 적재하지 않는다.
충격 시뮬레이션 결과 등 **계산된** 엣지는 별도 라벨(`:DERIVED`)을 붙이며 그래프에 영구 저장하지 않고 메모리/캐시에서만 다룬다.

## Indexes (v0)

```cypher
CREATE CONSTRAINT company_ticker IF NOT EXISTS
  FOR (c:Company) REQUIRE c.ticker IS UNIQUE;

CREATE CONSTRAINT company_corp_code IF NOT EXISTS
  FOR (c:Company) REQUIRE c.corp_code IS UNIQUE;

CREATE INDEX company_name_normalized IF NOT EXISTS
  FOR (c:Company) ON (c.name_normalized);
```

## Open Questions (to resolve before v1)

- 같은 회사의 지분율 변경을 어떻게 추적할 것인가? (시계열 엣지 vs 단일 엣지 + history)
- 비상장 자회사(거래소 종목코드 없음, DART corp_code는 있음)도 노드로 추가할 것인가?
- 외국 모회사(예: 삼성생명의 외국인 대주주)는 어떤 라벨로?
