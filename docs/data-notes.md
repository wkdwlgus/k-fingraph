# DART API 도메인 학습 노트

> **향후 docs/data-notes/ 디렉토리로 분리 시 매핑**:
>
> ```
> ## 공시검색 (list.json)                   → docs/data-notes/disclosure-list.md
> ## 기업개황 (company.json)                → docs/data-notes/company-overview.md
> ## 최대주주 현황 (hyslrSttus.json)        → docs/data-notes/major-shareholders.md
> ## 타법인 출자현황 (otrCprInvstmntSttus.json)
>                                            → docs/data-notes/other-corp-investments.md
> ## 대량보유 상황보고 (majorstock.json)    → docs/data-notes/major-stock-holdings.md
> ## 향후 v3·v4·v5 진입 시 추가 학습 필요 API 카탈로그
>                                            → docs/data-notes/future-tool-apis.md
> ```
>
> 분리 절차: 각 H2 블록을 위 매핑대로 새 파일로 잘라 옮기고 본 매핑 노트는 삭제.
> **각 H2 섹션은 자체 완결적으로 작성하며 다른 섹션을 cross-reference하지 않는다** —
> 분리 시 링크가 깨지지 않도록.
>
> 작성 시점: 2026-05-03. 사용 응답 표본: 삼성전자(corp_code=00126380),
> SK하이닉스(corp_code=00164779), bsns_year=2024, reprt_code=11011(연간 사업보고서).

---

## 공통 규칙

다음은 본 문서 내 모든 DART API 섹션이 공유하는 전제이다. 분리 시 각 파일 상단에 옮긴다.

- **인증키**: 모든 호출에 `crtfc_key` 필수. 환경변수 `DART_API_KEY`에서 로드.
- **엔드포인트 베이스**: `https://opendart.fss.or.kr/api/`
- **메서드/인코딩**: GET / UTF-8.
- **정상 응답 코드**: `status == "000"`. 다른 값은 모두 에러 (인증 실패, 파라미터 오류, 일일 한도 초과 등). 도메인 예외 `DartAPIError`로 변환 권장.
- **`bsns_year` 제약**: 정기보고서 단일항목 API들은 2015년 이후 데이터만 제공. 그 이전이 필요하면 별도 처리.
- **`reprt_code` 매핑**: `11011`=사업보고서(연간) / `11012`=반기 / `11013`=1분기 / `11014`=3분기.
- **숫자 포맷**: 거의 모든 수치 필드가 콤마 구분 문자열(예: `"508,157,148"`). Pydantic 파싱 시 정수/실수 변환 로직 필요.
- **결측 표현 혼재**: 같은 응답 안에서도 `"0"`, `"-"`, `""`이 결측을 표현하는 데 모두 등장. 파서가 이 셋을 통일된 sentinel(권장: `None`)로 정규화해야 함.
- **자기 자신만 corp_code**: 응답에 등장하는 `corp_code`는 호출 대상 회사의 것이다. 응답 내 등장하는 다른 회사·인물(예: 주주, 피투자회사, 대량보유자)은 **텍스트 이름만** 노출되며 corp_code 매핑은 별도 entity resolution 단계의 책임.
- **provenance 필드**: 모든 응답에 `rcept_no`(접수번호 14자리)가 포함된다. 그래프 적재 시 엣지의 출처 ID로 활용.

---

## 공시검색 (list.json)

회사가 어떤 공시를 어느 시점에 냈는지 정찰하는 엔드포인트. 본 v0 그래프 적재의
직접 소스는 아니지만, 단일항목 API 호출 전 "어떤 사업연도/보고서가 존재하나"를
확인하거나 v8 ops에서 신규 공시를 모니터링할 때의 진입점.

### 호출 명세

- 엔드포인트: `https://opendart.fss.or.kr/api/list.json`
- 필수: `crtfc_key`
- 자주 쓰는 옵션: `corp_code`(특정 회사로 좁힘), `bgn_de`/`end_de`(YYYYMMDD,
  `corp_code` 없으면 최대 3개월 범위), `pblntf_ty`/`pblntf_detail_ty`(공시 유형),
  `last_reprt_at`(최종보고서만), `page_no`/`page_count`(1~100, 기본 10).

### 응답 키 (top-level)

`status`, `message`, `page_no`, `page_count`, `total_count`, `total_page`, `list`.

### `list[]` 항목 필드 (관찰 기준 9개)

| 필드 | 의미 | 비고 |
|---|---|---|
| `corp_code` | 보고자 corp_code (8자리) | |
| `corp_name` | 회사명 | |
| `stock_code` | 종목코드 (6자리) | 비상장은 빈 값 |
| `corp_cls` | 법인 구분 (Y/K/N/E) | Y=유가, K=코스닥, N=코넥스, E=기타 |
| `report_nm` | 공시 제목 | 끝에 trailing 공백 다수 관찰 — strip 필요 |
| `rcept_no` | 접수번호 (14자리, YYYYMMDD + 일련번호) | |
| `flr_nm` | 공시 제출자 | |
| `rcept_dt` | 접수일자 (YYYYMMDD) | |
| `rm` | 비고 | 거의 빈 문자열 또는 "유" |

### 관찰사항

- 페이징 응답에 `total_count`/`total_page`가 함께 와서 caller가 다음 페이지를 알 수 있음.
- `report_nm` 끝에 공백이 다수 있는 경우 관찰됨 (예: `"투자판단관련주요경영사항              "`). 파서에서 `.strip()` 적용해야 의미있는 분류 가능.
- `corp_code` 없이 호출 시 기간이 자동으로 3개월로 좁혀짐 — 광범위 모니터링은 corp_code 단위로 분할 호출이 사실상 강제됨.

---

## 기업개황 (company.json)

`Company` 노드의 부가 필드(영문명·CEO·업종·주소 등)를 채우는 가벼운 엔드포인트.
회사당 1회 호출, 호출 비용 거의 무료(일일 한도 내).

### 호출 명세

- 엔드포인트: `https://opendart.fss.or.kr/api/company.json`
- 필수: `crtfc_key`, `corp_code`

### 응답 필드 → Company 노드 매핑 가이드

| 응답 필드 | 의미 | 권장 노드 매핑 |
|---|---|---|
| `corp_name` | 한글 정식 회사명 | `Company.name` (이미 corpCode 표에서 보유) |
| `corp_name_eng` | 영문 회사명 | `Company.name_eng` (신규) |
| `stock_name` | 주식 약칭 | `Company.stock_name` (옵션) |
| `stock_code` | 거래소 종목코드 (6자리) | `Company.ticker` (이미 보유) |
| `ceo_nm` | 대표자명 | `Company.ceo_name`. 향후 v4 사람 노드 도입 시 EXECUTIVE_OF 엣지로 승격 가능 |
| `corp_cls` | 법인 구분 (Y/K/N/E) | `Company.market_segment` |
| `jurir_no` | 법인등록번호 | `Company.jurir_no` (잠재 식별자) |
| `bizr_no` | 사업자등록번호 | `Company.biz_no` (잠재 식별자) |
| `adres` | 본사 주소 | `Company.address` (옵션, 지역 분석용) |
| `hm_url`, `ir_url` | 홈페이지 / IR 페이지 | `Company.urls` (옵션) |
| `phn_no`, `fax_no` | 전화·팩스 | 그래프엔 부적합 — skip |
| `induty_code` | 한국표준산업분류(KSIC) 코드 | `Company.industry_code` — **v4 유사종목 발굴의 핵심 속성** |
| `est_dt` | 설립일자 (YYYYMMDD) | `Company.est_date` |
| `acc_mt` | 결산월 (MM) | `Company.fiscal_month` |

### 관찰사항

- 표본 두 회사 모두 18개 필드 모두 채워짐(상장 대기업 기준). 비상장·소규모 기업은 결측 가능성 있음 — 적재 시 모든 필드 Optional 처리 권장.
- `induty_code`는 KSIC 한국표준산업분류 코드(예: 26410). 이 코드 분류표는 별도 통계청 API/데이터 필요. v4 진입 시 같이 학습.
- `est_dt`로 회사 나이를 계산할 수 있어 v3 시뮬레이션의 가중치(신생사 vs 노포)에 활용 가능.
- **`corp_name` 표기 차이 주의**: corpCode 표(`/api/corpCode.xml`)는 "삼성전자"처럼
  법인형 약자 없이 짧게 응답하지만, `company.json`은 "삼성전자(주)"처럼 법인형
  표기까지 포함해서 응답한다. v0 그래프에서 `Company.name`을 어느 쪽으로 정규화할지
  결정 필요 — 권장: corpCode 표 형태(짧은 형태)를 canonical로 두고 company.json의
  긴 형태는 `name_full` 같은 별도 속성으로 보존. v2 entity resolution sprint에서
  법인형 약자(`㈜`, `(주)`, `주식회사`, `Co., Ltd.` 등) 정규화 규칙 도입.

---

## 최대주주 현황 (hyslrSttus.json)

회사의 최대주주 본인 + 그 특수관계인 목록. **OWNS 엣지의 역방향 소스** — "이 회사를
누가 소유하고 있는가". 정기보고서 기준이라 연 1~4회 갱신.

### 호출 명세

- 엔드포인트: `https://opendart.fss.or.kr/api/hyslrSttus.json`
- 필수: `crtfc_key`, `corp_code`, `bsns_year`(YYYY), `reprt_code`(11011/11012/11013/11014)

### 응답 키 (top-level)

`status`, `message`, `list`.

### `list[]` 항목 필드 (관찰 기준 13개)

| 필드 | 의미 | 비고 |
|---|---|---|
| `rcept_no` | 출처 보고서 접수번호 | provenance |
| `corp_code` | 호출 대상 회사의 corp_code | 자기 자신 |
| `corp_name` | 호출 대상 회사명 | |
| `corp_cls` | 법인 구분 | |
| `stock_knd` | 주식의 종류 | "보통주" / "의결권 있는 주식" 등 표기 다양 |
| `nm` | **주주 이름** (개인명 또는 회사명) | corp_code 매핑 없음, 텍스트만 |
| `relate` | 관계 | "최대주주 본인", "최대주주", "특수관계인", "친인척" 등 |
| `bsis_posesn_stock_co` | 기초 보유 주식수 | 콤마 구분 문자열 |
| `bsis_posesn_stock_qota_rt` | 기초 지분율 (%) | 문자열 |
| `trmend_posesn_stock_co` | 기말 보유 주식수 | 콤마 구분 문자열 |
| `trmend_posesn_stock_qota_rt` | 기말 지분율 (%) | 문자열 |
| `rm` | 비고 | "-" 또는 텍스트 |
| `stlm_dt` | 결산일 | YYYY-MM-DD 포맷 (다른 API와 다름!) |

### 관찰사항

- **주주 이름이 텍스트만 옴**(`nm`) — 회사인 경우(예: "삼성생명보험㈜") 별도 entity resolution으로 corp_code 매핑 필요. 한자(㈜) 포함, 정규화 필요.
- 응답 건수: 삼성전자 26건, SK하이닉스 15건 — 특수관계인 포함이라 회사별 편차 큼.
- **`stlm_dt` 포맷이 `YYYY-MM-DD`** — 다른 DART 응답의 `YYYYMMDD`와 불일치. 파서가 두 포맷 모두 처리해야 함.
- `relate`가 자유 텍스트라 분류용으로 쓰려면 사전 정의된 enum 매핑 필요 (Day 3 스키마 설계 시 결정).

---

## 타법인 출자현황 (otrCprInvstmntSttus.json)

회사가 다른 법인에 출자한 현황. **OWNS 엣지의 정방향 소스 — v0 그래프의 핵심**.
이 응답이 곧 "A 회사가 B 회사 지분을 X% 갖고 있다"는 트리플로 변환된다.

### 호출 명세

- 엔드포인트: `https://opendart.fss.or.kr/api/otrCprInvstmntSttus.json`
- 필수: `crtfc_key`, `corp_code`, `bsns_year`(YYYY), `reprt_code`(11011/11012/11013/11014)

### 응답 키 (top-level)

`status`, `message`, `list`.

### `list[]` 항목 필드 (관찰 기준 20개)

OWNS 엣지 적재에 핵심인 필드만 굵게 표기.

| 필드 | 의미 | 비고 |
|---|---|---|
| `rcept_no` | 출처 보고서 접수번호 | provenance |
| `corp_code` | 호출 대상 회사 (출자한 쪽) | OWNS의 source 노드 |
| `corp_name` | 호출 대상 회사명 | |
| `corp_cls` | 법인 구분 | |
| **`inv_prm`** | **피투자회사명** | **OWNS의 target 노드 (텍스트만, corp_code 없음 → ER 필요)** |
| `frst_acqs_de` | 최초 취득일자 | 포맷 `YYYY.MM.DD` (점 구분, 또 다른 변형!) |
| `invstmnt_purps` | 출자 목적 | "경영참여", "단순투자" 등 |
| `frst_acqs_amount` | 최초 취득 금액 | 콤마 구분 |
| `bsis_blce_qy` | 기초 보유 주식수 | |
| `bsis_blce_qota_rt` | 기초 지분율 (%) | |
| `bsis_blce_acntbk_amount` | 기초 장부가액 | |
| `incrs_dcrs_acqs_dsps_qy` | 기중 증감 (취득·처분) 수량 | "0" 또는 "-" 결측 혼재 |
| `incrs_dcrs_acqs_dsps_amount` | 기중 증감 금액 | 동상 |
| `incrs_dcrs_evl_lstmn` | 기중 평가 손익 | |
| **`trmend_blce_qy`** | **기말 보유 주식수** | OWNS 엣지 가중치 후보 |
| **`trmend_blce_qota_rt`** | **기말 지분율 (%)** | **OWNS 엣지의 핵심 가중치** |
| `trmend_blce_acntbk_amount` | 기말 장부가액 | |
| `recent_bsns_year_fnnr_sttus_tot_assets` | 피투자회사 최근 사업연도 총자산 | 가중치 후보 |
| `recent_bsns_year_fnnr_sttus_thstrm_ntpf` | 피투자회사 최근 사업연도 당기순이익 | |
| `stlm_dt` | 결산일 | YYYY-MM-DD |

### 관찰사항

- 응답 건수: 삼성전자 138건(전세계 자회사·관계사 다수), SK하이닉스 49건. 회사 규모에 따라 큰 편차.
- **`inv_prm`(피투자회사)이 텍스트만** — corp_code 매핑은 ER 단계의 책임. v2 Entity Resolution sprint의 1차 매칭 대상.
- **날짜 포맷이 또 다름**: `frst_acqs_de`는 `YYYY.MM.DD`(점 구분), `stlm_dt`는 `YYYY-MM-DD`. 같은 응답 안에서도 혼재. 파서가 다중 포맷 지원 필수.
- 기중 증감 필드의 결측이 `"0"`, `"-"`로 혼재 — `"0"`은 진짜 변동 없음일 수도 있고 결측일 수도 있어 의미 모호. Day 3 스키마 설계 시 의미 결정 필요.
- **Day 3 스키마 설계 시 주의점**:
  - OWNS 엣지의 source는 `corp_code`(확실), target은 `inv_prm`(텍스트, 후속 ER 단계에서 corp_code로 변환)으로 적재.
  - 가중치는 `trmend_blce_qota_rt`(지분율 %)를 0.0~1.0 float으로 정규화 권장.
  - 같은 (source, target) 페어가 보고서마다 갱신되므로 적재는 멱등(`MERGE`) + provenance(`rcept_no`) 보존.

---

## 대량보유 상황보고 (majorstock.json)

5% 이상 지분을 새로 보유하거나 변동했을 때 자본시장법에 따라 의무 신고하는 보고서.
**정기보고서와 본질적으로 다른 비정기 이벤트성 데이터** — 이벤트 발생 시점에 즉시
공시되며 사업연도/분기 개념이 없다.

### 호출 명세

- 엔드포인트: `https://opendart.fss.or.kr/api/majorstock.json`
- 필수: `crtfc_key`, `corp_code` 만 (사업연도·보고서종류 파라미터 없음)

### 응답 키 (top-level)

`status`, `message`, `list`.

### `list[]` 항목 필드 (관찰 기준 13개)

| 필드 | 의미 | 비고 |
|---|---|---|
| `rcept_no` | 접수번호 | provenance |
| `rcept_dt` | 접수일자 | YYYY-MM-DD 포맷 |
| `corp_code` | 신고 대상 회사 (피보유) | OWNS의 target |
| `corp_name` | 회사명 | |
| `report_tp` | 보고 유형 | "일반" / "약식" 두 종류 관찰 |
| `repror` | **보고자 이름** (개인·기관·외국인 혼재) | corp_code 없음, ER 필요 |
| `stkqy` | 보고자 보유 주식수 | 콤마 구분 |
| `stkqy_irds` | 직전 보고 대비 증감 | 음수 가능 (예: "-62,823") |
| `stkrt` | 보고자 지분율 (%) | 5.00 이상 |
| `stkrt_irds` | 지분율 증감 | 음수 가능 |
| `ctr_stkqy` | 공동보유자 합산 주식수 | "-" 결측 |
| `ctr_stkrt` | 공동보유자 합산 지분율 | "-" 결측 |
| `report_resn` | 보고 사유 (자유 텍스트) | "신규 보고의무 발생", "보유주식수 변동" 등 |

### 관찰사항

- 응답 건수: 삼성전자 40건, SK하이닉스 11건 (시간 누적, 기간 제한 없이 전체 반환).
- **보고자(`repror`)가 매우 다양**: 국내 기업("삼성물산"), 외국 기관("TheCapitalGroupCompanies,Inc."), 개인 등. ER가 정기보고서보다 어려움.
- **정기보고서(hyslrSttus)와 중복·차이 패턴**:
  - 둘 다 5%+ 대주주를 다루지만 시점이 다름. hyslrSttus는 결산일 스냅샷, majorstock는 이벤트 발생 시점.
  - 같은 보고자가 두 곳 모두에 등장 가능 → 적재 시 출처(`rcept_no`)를 보존해 두 신호를 구분 유지.
  - majorstock 단독으로 잡히는 보고자(외국 기관 투자자)도 흔함 — OWNS 엣지의 외연 확장.
- **`stkqy_irds`/`stkrt_irds` 음수**: 콤마 + 음의 부호 조합 파싱 주의 (예: "-62,823").
- **그래프 적재 관점**: 정기보고서(연 단위)와 majorstock(실시간)의 cadence 차이가 v8 ops에서 폴링 주기를 분리해야 하는 근거.

---

## 향후 v3·v4·v5 진입 시 추가 학습 필요 API 카탈로그

본 v0에서 학습한 5개 API는 `Company` 노드 + `OWNS` 엣지(정/역방향 + 5% 보고)로
구성된 v0 그래프를 채우는 데 충분하다. 그러나 v3 충격 시뮬레이션·v4 유사 종목
발굴·v5 포트폴리오 리스크 분석은 더 풍부한 노드/엣지/속성/시계열을 요구한다.
아래는 각 도구 sprint 진입 시 학습·적재해야 할 API 목록이다. **각 sprint 진입
시점에 schema 확장 ADR을 먼저 작성한 뒤 본 카탈로그에서 필요 API를 골라 학습**한다.

### v3 충격 전파 시뮬레이션 — 위기 이벤트 + 시계열 + 노드 가중치

| apiId | API명 | 어떻게 쓰일지 |
|---|---|---|
| DS002/2019008 | 최대주주 변동현황 | OWNS 엣지의 시계열 변동 (충격 전파 시점 정확화) |
| DS003/2019016 | 단일회사 주요계정 | Company 노드의 재무 가중치 (자산·매출·순이익) |
| DS003/2022001 | 단일회사 주요 재무지표 | 부채비율·ROE — 위기 취약성 신호 |
| DS005/2020019 | 부도발생 | Event 노드 (백테스트 그라운드 트루스) |
| DS005/2020020 | 영업정지 | Event 노드 |
| DS005/2020021 | 회생절차 개시신청 | Event 노드 |
| DS005/2020022 | 해산사유 발생 | Event 노드 |
| DS005/2020027 | 채권은행 등의 관리절차 개시 | Event 노드 |
| DS005/2020028 | 소송 등의 제기 | Event (선후행 신호) |
| DS005/2020042-2020043 | 영업양수·양도 결정 | 구조 변경 이벤트 (전파 경로 동적 변화) |
| DS005/2020046-2020047 | 타법인 주식 양수·양도 결정 | OWNS 엣지의 이벤트성 변동 (정기보고서 사이의 공백 채움) |
| DS005/2020050-2020053 | 합병·분할·교환 결정 | 노드 자체의 생성·소멸 이벤트 |

### v4 유사 종목 발굴 — 노드·엣지 다양성 (Node2Vec/GraphSAGE 임베딩 풍부도)

| apiId | API명 | 어떻게 쓰일지 |
|---|---|---|
| DS002/2019010 | 임원 현황 | `Person` 노드 + `EXECUTIVE_OF` 엣지. 임원 겸직이 회사 간 약한 유사성 신호 |
| DS002/2020009 | 회계감사인 명칭·의견 | `AuditFirm` 노드 + `AUDITED_BY` 엣지. 같은 감사인 = 약한 신호 |
| DS002/2020012 | 사외이사 및 그 변동현황 | `Person` 노드 보강 (사외이사 겸직 그래프) |
| DS003/2019016 | 단일회사 주요계정 | 재무 유사성 벡터 |
| DS003/2022001 | 단일회사 주요 재무지표 | 정규화된 재무 유사성 (규모 무관 비교) |
| (이미 v0 학습) DS001/2019002 기업개황의 `induty_code` | 업종 코드 | `Company.industry_code` 속성 또는 `SIMILAR_INDUSTRY` 엣지 |

### v5 포트폴리오 리스크 분석 — 중심성·커뮤니티·노출도

v3·v4 카탈로그 대부분이 그대로 재사용된다 — 풍부한 그래프 위에서 centrality 계산
및 Louvain 커뮤니티 검출이 의미를 가진다. v5 고유 추가 항목:

| apiId | API명 | 어떻게 쓰일지 |
|---|---|---|
| DS004/2019022 | 임원·주요주주 소유보고 | `Person`·`Institution` 보유 정보 — Person→Company 엣지의 외연 확장 |
| DS003/2022001-2022002 | 주요 재무지표 (단일/다중) | 노출도 가중치 (시총·부채비율·유동성) |
| (이미 v0 학습) DS002/2019015 타법인 출자현황 | OWNS 정방향 | 가중치(지분율) 그대로 사용 — 노출도 전파의 기본 |

### 공통 비고

- v3·v4·v5 진입 시 schema 확장 필요: `Person` / `Institution` / `AuditFirm` / `Event`
  노드 신설 가능성 — 각 진입 시 ADR 작성 후 `docs/schema.md` 갱신.
- DS005 시리즈는 이벤트성이라 정기 폴링이 부적합 — webhook 또는 짧은 polling 패턴
  필요 (v8 ops에서 cadence 결정).
- 본 카탈로그는 "잊지 않게 적어둔 목록"이며, 실제 학습 깊이와 우선순위는 각 sprint
  진입 시점에 그 도구의 KPI를 기준으로 다시 결정한다.
