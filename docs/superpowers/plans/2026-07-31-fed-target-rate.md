# FRED 연준 목표금리 중간값 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 월별 수집기에 FRED 연준 목표금리 범위의 중간값을 추가한다.

**Architecture:** 기존 FRED 요청·파싱 경로를 시리즈 ID 기반으로 재사용하고, `DFEDTARU`와 `DFEDTARL`의 월별 값을 `Decimal`로 계산해 변환 계층에서 ECOS·PPI와 합친다. 원본 JSON은 출처별 접두사를 분리하고, 대시보드는 기존 공개 CSV를 통해 새 컬럼을 자동으로 읽는다.

**Tech Stack:** Python 3.9+, Python 표준 라이브러리, `unittest`, FRED JSON API.

## Global Constraints

- 기존 `WPU1017` 철강 PPI와 ECOS 기준금리의 요청·출력 호환성을 유지한다.
- `DFEDTARU`와 `DFEDTARL`이 모두 있는 월만 중간값을 계산한다.
- API 키와 원본 응답의 비밀 값은 로그·문서·생성 파일에 노출하지 않는다.
- 외부 패키지를 추가하지 않는다.

---

### Task 1: FRED 시리즈 수집과 연준 금리 계산 테스트

**Files:**
- Modify: `tests/test_fred.py`
- Modify: `tests/test_transform.py`

**Interfaces:**
- `fetch_fred(api_key, date_range, series_id="WPU1017", opener=urlopen)` keeps the existing default.
- `parse_fred(payload)` continues returning `{YYYY-MM: numeric_text_or_None}`.
- New `calculate_target_rate(upper_values, lower_values)` returns monthly midpoint strings or `None`.

- [ ] **Step 1: Write failing tests**

Add a request test asserting `series_id="DFEDTARU"` is sent when requested, and add midpoint tests for equal months, missing bounds, and decimal precision.

- [ ] **Step 2: Run focused tests and verify failure**

Run `python3 -m unittest tests.test_fred tests.test_transform -v` from the repository root. Expected: the new series argument and midpoint helper tests fail because the interfaces are not implemented.

- [ ] **Step 3: Commit test-only changes**

Run `git add tests/test_fred.py tests/test_transform.py && git commit -m "test: specify fed target midpoint collection"`.

### Task 2: Implement FRED series support and monthly midpoint

**Files:**
- Modify: `collector/fred.py`
- Modify: `collector/transform.py`

**Interfaces:**
- `fetch_fred` accepts an optional `series_id` while preserving the old default.
- `calculate_target_rate` intersects upper/lower month keys, returns sorted monthly values, and rejects an empty usable result with `CollectorError`.

- [ ] **Step 1: Implement the optional FRED series ID**

Replace the hard-coded `WPU1017` query value with the `series_id` parameter defaulting to `WPU1017`; leave all network and error handling unchanged.

- [ ] **Step 2: Implement midpoint calculation**

Parse non-missing bound strings with `Decimal`, calculate `(upper + lower) / 2`, format with fixed-point text, and preserve `None` for missing bounds.

- [ ] **Step 3: Run focused tests and verify green**

Run `python3 -m unittest tests.test_fred tests.test_transform -v`. Expected: all focused tests pass.

### Task 3: Integrate sources and persist the new column

**Files:**
- Modify: `collect_data.py`
- Modify: `collector/storage.py`
- Modify: `tests/test_collect_data.py`
- Modify: `tests/test_storage.py`

**Interfaces:**
- `collect_data.run` fetches WPU1017, DFEDTARU, DFEDTARL, and ECOS using the existing key and saves three distinct FRED raw responses.
- `merge_monthly` accepts the calculated Fed midpoint and emits `us_fed_target_rate_percent`.
- `CSV_FIELDS` includes the new field.

- [ ] **Step 1: Write failing orchestration and CSV tests**

Extend the workflow test to expect three FRED fetches, midpoint data passed to `merge_monthly`, and a new CSV field; extend storage assertions to require the field in the header.

- [ ] **Step 2: Run tests and verify failure**

Run `python3 -m unittest tests.test_collect_data tests.test_storage -v`. Expected: assertions fail because the workflow still fetches one FRED series and the CSV schema has two indicators.

- [ ] **Step 3: Implement integration**

Fetch and parse the three FRED series, save raw responses with `fred_steel_ppi`, `fred_fed_target_upper`, and `fred_fed_target_lower`, calculate the midpoint, pass it to `merge_monthly`, and update progress messages to show all four sources.

- [ ] **Step 4: Run focused integration tests**

Run `python3 -m unittest tests.test_collect_data tests.test_storage tests.test_transform -v`. Expected: all pass.

### Task 4: Update documentation and run the full suite

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-30-economic-data-collector-design.md`

- [ ] **Step 1: Document the new series and output field**

Document `DFEDTARU`, `DFEDTARL`, the midpoint formula, the new CSV column, and the additional raw filenames without including any key value.

- [ ] **Step 2: Run the full test suite**

Run `python3 -m unittest discover -s tests -v`. Expected: `OK` with no failures or errors.

- [ ] **Step 3: Inspect the diff and commit the implementation**

Run `git diff --check`, inspect `git diff --stat`, then commit with `git add collector collect_data.py tests README.md docs/superpowers/specs/2026-07-30-economic-data-collector-design.md && git commit -m "feat: add fed target rate indicator"`.
