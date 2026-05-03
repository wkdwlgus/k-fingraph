# ADR 0008: v0 OWNS endpoint resolution — exact normalized-name match with universe priority

- Status: Accepted
- Date: 2026-05-03

## Context

DART periodic report responses identify only the calling company by
`corp_code` — the other endpoint of an OWNS edge (the investee in
`otrCprInvstmntSttus`, the holder in `hyslrSttus`) arrives as text only.

ADR 0007 specifies the v0 loader's filter: an `OwnsCandidate` is loaded only
when both endpoints carry a `corp_code` AND both `corp_code` values lie inside
the KOSPI 200 universe. Without a step that fills in `corp_code` on the text
side, **every** candidate fails the first half of that filter (one endpoint
is always None) — the v0 1차 적재 dry run measured this directly: 10,499
candidates extracted, 0 loaded, 10,499 dropped as endpoint-unresolved.

`docs/architecture.md` Ingestion step 4 already states that v0 ER is
"단순 키 매칭 (ticker / corp_code 직접 비교)". This ADR pins down the
operational policy: which key, what to do on ambiguity, what to skip.

## Decision

**Resolve text endpoints by exact match on `name_normalized` against the
DART corp_code reference table, with the following priority and exclusions.**

Implementation: `src/k_fingraph/resolve/owns.py`.

### Priority on ambiguity

When multiple corp_codes share the same normalized name, the resolver picks
in this order:

1. **Universe (KOSPI 200) corp_code** — the candidate becomes loadable as
   an OWNS edge.
2. **Listed corp_code outside the universe** (`stock_code is not None`) —
   the loader will then drop as "outside universe" (classified A by
   diagnostics; recovered when v0.5 expands the universe).

Within each tier, first-write-wins via `dict.setdefault`. KOSPI 200 internal
duplicates are extremely rare; this is a deterministic tie-break, not a
quality choice.

### Exclusion: unlisted corp_codes

Unlisted DART entities (`stock_code is None`) are deliberately **not** in
the resolution index. The reason: resolving an OWNS endpoint to an unlisted
corp_code would put it on the loader's "outside universe" path (classified
A — "universe will fix this"), which is misleading. v0.5's universe
expansion to all KOSPI + KOSDAQ would NOT recover unlisted candidates,
because they are not on any exchange. The honest classification is B-1
(schema limit — needs an `:UnlistedCompany` node), and leaving them
text-unresolved keeps the diagnostic classifier in charge.

### Exclusion: fuzzy / embedding-based matching

Out of scope for v0. Reserved for the v2 Entity Resolution sprint. Any
text endpoint whose normalized name does not appear verbatim in the
corp_code table stays unresolved.

## Rationale

- **Architecture.md compliance** — "단순 키 매칭" was already the v0 ER
  decision. This ADR is the operational realization, not a new policy
  direction.
- **Universe priority is the v0 product** — every OWNS edge that ends up
  in the graph is a candidate that resolved into the universe. Choosing
  universe-first when ambiguous makes the loaded edge set behave like a
  function of the universe, not of corp_code table iteration order.
- **Unlisted exclusion preserves diagnostic accuracy** — the (A)/(B-1)/(B-2)
  split in ADR 0007 follow-up only carries actionable information if each
  bucket really represents what it claims. Including unlisted matches in
  the index would inflate (A) at the expense of (B-1), making v0.5
  universe-expansion projections too optimistic.
- **Empirical evidence** — measured directly against the 1차 적재:
  - resolver disabled: A 300 / B-1 3,235 / B-2 6,964, OWNS loaded 0
  - resolver enabled (this ADR): A 338 / B-1 2,948 / B-2 6,964, OWNS loaded 242
  - The B-1 reduction (287) and the loaded count (242, MERGE-deduplicated
    from 287 by same-disclosure repeats) are the same population — that's
    the universe-priority effect, isolated. The A increase (38) is the
    listed-fallback effect — also isolated.

## Consequences

### Positive

- v0 graph has a meaningful number of OWNS edges (236 in the 1차 적재) with
  hub-and-spoke structure that ADR 0007 predicted (Samsung group cross-
  holdings, Hyundai Motor group, financial holding companies → subsidiary
  banks/insurance).
- The (A) bucket count is now an honest baseline for v0.5: every (A) drop
  IS a candidate that v0.5's universe expansion is designed to recover.
- The resolution step is a pure function of (candidates, index) — fully
  unit-testable without Neo4j or DART.

### Negative / cost

- Names that DART uses inconsistently across responses (e.g. "삼성전자(주)" vs
  "삼성전자주식회사" vs "삼성전자") will only resolve when our normalizer
  collapses them to the same string. The v0 normalizer (`_CORP_FORM_SUFFIXES`
  in `sources/dart_reports.py`) handles the common Korean suffixes; novel
  variants will silently miss-match and end up in (B-2).
- This is not addressable within v0 without going to fuzzy matching — the
  v2 ER sprint owns it.

### 후속 작업

- v0.5 sprint enters: re-measure the (A)/(B-1)/(B-2) split after universe
  expansion. Compare against this ADR's baseline (A 338 / B-1 2,948 / B-2 6,964).
  Confirm (A) drops to near-zero (universe-expansion working) and (B-1)
  drops modestly (resolution catches a few KOSDAQ-listed names whose v0
  matches were ambiguous).
- v2 ER sprint: this ADR is superseded by the v2 ER policy. The new ADR
  decides on text embedding model, similarity threshold, and how to handle
  the names that v0's exact matcher missed.

## Supersedes / Superseded by

- 없음 (architecture.md "v0: 단순 키 매칭"의 운영 정책 보강).
- v2 ER sprint 진입 시 supersede 대상.
