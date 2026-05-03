# Current Sprint: v0.5 (적재 universe 확장)

목표: 적재 universe를 KOSPI 200에서 **전체 KOSPI + KOSDAQ**으로 확장하여,
v0에서 매칭 실패로 폐기된 후보 중 (A) 종류(다른 상장사라 매칭 실패)를 즉시
해소. v0 적재 후 측정해 둔 분류(A 338 / B-1 2,948 / B-2 6,964, ADR 0008)와
비교해 (A) 감소량을 정량 입증한다.

비상장사·외국 법인·개인·SPC 등 (B) 종류는 본 sprint 범위 밖이며 schema 확장
sprint(v3 Person, v4 AuditFirm 등)에서 점진 해소된다.

## 진입 전 결정 재검토 (first-class — 망각 금지)

CLAUDE.md sprint 진입 절차에 따라 본 sprint 이름이 "재검토 트리거" 컬럼에
등장하는 ADR을 모두 펼쳐 읽고, 그 결과를 본 sprint의 작업 단위로 변환한다.

- [x] **ADR 0007 (v0 OWNS 적재 범위) supersede** — ADR 0009 신설 (universe
      정의 = KOSPI 보통주 + KOSDAQ 보통주 corp_codes). ADR 0007 Status를
      `Superseded by ADR 0009 (2026-05-04)`로 갱신, 본문 보존.
      `docs/decisions/README.md` 인덱스 동기화 완료
- [x] **ADR 0008 (v0 OWNS endpoint 해소)** — universe 확장 후 (A)/(B-1)/(B-2)
      재측정 완료: A **338 → 181 (-46%)**, B-1 2,948 → 16,553, B-2 6,964 → 29,743.
      `docs/progress.md` v0.5 섹션에 표로 기록. (A) 잔여 분석은 ADR 0009 본문

## 작업 단위

- [x] KRX 정보데이터시스템에서 KOSPI 전 종목·KOSDAQ 전 종목 수집
  (v0의 KOSPI 200 수집과 같은 EUC-KR → UTF-8 변환 절차) — KOSPI 839 +
  KOSDAQ 1,820 = 2,659 회사 (보통주 필터). raw는 `data/raw/krx/`,
  정제본은 `data/reference/{kospi,kosdaq}_all.csv`
- [x] 각 종목 → DART corp_code 매핑 (`sources/extended_universe.py`로
  일반화). 캐시된 corp_code XML 대비 매칭률 **100%** (2,659/2,659)
- [x] 종목 메타에 `market` 구분(KOSPI / KOSDAQ) 부착 — `UniverseConstituent`
  / `UniverseMembership`에 `market` 필드, 적재 시 `Company.market`로 그대로
  전달. schema 변경 없음
- [x] 적재 필터 갱신 — `scripts/load_v05.py` 신규 entry point.
  `load_v0.py`는 frozen artifact로 보존. universe 진입점만 교체하고
  필터·ER·분류 로직은 v0 그대로 재사용
- [x] 확장 universe로 forward + reverse OWNS 재추출·재적재 (idempotent) —
  walltime 59분, 그래프 Company 200 → 2,659 / OWNS 236 → 2,347
- [x] 매칭 실패 분류 재측정 — `data/processed/v05_load/report.json`에 풀
  classification 보존, 핵심 수치는 `docs/progress.md` v0.5 섹션 표
- [ ] (선택) Streamlit 워크벤치 selectbox 옵션이 2,659개로 늘어남.
  체감 확인 필요. 견디지 못하면 `_company_index.search_companies`를
  활용한 autocomplete 패턴으로 전환 — 검색 헬퍼는 v0에서 미리 분리해 둠

## Definition of Done (v0.5)

- [x] 확장 universe 적재 결과: 회사 노드 2,659 (목표 ~2,400 초과),
  OWNS 엣지 236 → 2,347 (+9.9×)
- [~] (A) 종류 매칭 실패 카운트가 v0 baseline 338 → 0 또는 그에 가까운 값:
  **부분 달성** 338 → 181 (-46%). 잔여는 상장폐지·DART historical
  stock_code 구조에서 비롯되며 universe 확장으로는 영구 해소 불가.
  ADR 0009 본문에 정직하게 기록
- [x] ADR 0007을 supersede하는 신규 ADR + 인덱스 갱신 (ADR 0009)
- [x] `uv run pytest -m "not e2e"` 0 fail
- [x] `uv run ruff check . && uv run mypy src/` 0 error
- [ ] git tag `v0.5.0` (사용자 승인 후)

## Blocked / Questions

- 없음 (KRX·DART·Aura 모두 v0에서 검증 완료. 전체 KOSPI/KOSDAQ CSV는 KRX
  정보데이터시스템에서 v0 KOSPI 200과 동일한 절차로 수집 가능)
