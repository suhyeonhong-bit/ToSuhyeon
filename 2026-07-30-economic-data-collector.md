# ECOS·FRED Data Collector and GitHub Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a beginner-friendly Python program that collects five years of monthly ECOS base-rate and FRED steel-PPI data, preserves raw JSON, creates a merged CSV, and runs every Monday at 11:00 Asia/Seoul in GitHub Actions with data-only automatic commits.

**Architecture:** A small standard-library Python package separates configuration, date calculation, provider-specific HTTP/parsing, transformation, and atomic storage. One CLI orchestrates those units locally and in GitHub Actions; the workflow tests before collecting and commits only generated data. The same code reads local keys from `.env` or GitHub keys from environment variables.

**Tech Stack:** Python 3.9.6+, Python standard library (`unittest`, `urllib`, `json`, `csv`, `decimal`, `tempfile`), Git, GitHub Actions (`actions/checkout@v6`, `actions/setup-python@v6`)

## Global Constraints

- Work in `/Users/suhyeonhong/Documents/GitHub/ToSuhyeon`.
- Follow `docs/superpowers/specs/2026-07-30-economic-data-collector-design.md`.
- Support Python 3.9.6 and later without installing third-party Python packages.
- Show beginner-facing progress and failure messages in easy Korean.
- Never print, commit, store in generated data, or place in command arguments the real FRED or ECOS API keys.
- Local secrets come from `.env`; GitHub secrets come from `FRED_API_KEY` and `ECOS_API_KEY` environment variables.
- Collect FRED series `WPU1017` and ECOS table/item `722Y001` / `0101000` with monthly frequency.
- Use the current month and the same month five years earlier as an inclusive range.
- Keep every successful raw JSON response and replace the processed CSV only after a complete successful write.
- Tests must not read the real `.env`, use the real keys, or access the network.
- GitHub automation targets the public fork `suhyeonhong-bit/ToSuhyeon`.
- Schedule weekly execution for Monday 11:00 with `timezone: "Asia/Seoul"`.
- Grant the workflow only `contents: write`; do not add a pull-request trigger.
- Automatic commits may stage only `data/raw` and `data/processed/monthly_indicators.csv`.

---

## File Map

- `collector/errors.py`: one safe user-facing exception type.
- `collector/config.py`: load keys from environment variables or local `.env`.
- `collector/dates.py`: calculate the inclusive five-year API date range.
- `collector/fred.py`: build the FRED request and parse `WPU1017`.
- `collector/ecos.py`: build the ECOS request and parse `722Y001 / 0101000`.
- `collector/transform.py`: merge provider values by month.
- `collector/storage.py`: atomically store raw JSON and the processed CSV.
- `collect_data.py`: orchestrate one collection run and print Korean progress.
- `.github/workflows/collect-weekly.yml`: test, collect, and commit data weekly or on manual dispatch.
- `tests/fixtures/*.json`: small public sample responses with no secrets.
- `tests/test_*.py`: standard-library unit tests.
- `data/raw/.gitkeep`, `data/processed/.gitkeep`: retain generated-data directories before the first run.
- `README.md`: beginner instructions for local and GitHub execution.

---

### Task 1: Safe Configuration and Five-Year Date Range

**Files:**
- Create: `collector/__init__.py`
- Create: `collector/errors.py`
- Create: `collector/config.py`
- Create: `collector/dates.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `tests/test_dates.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `CollectorError(message: str)`.
- Produces: `Config(fred_api_key: str, ecos_api_key: str)`.
- Produces: `load_config(env_path: Path, environ: Optional[Mapping[str, str]] = None) -> Config`.
- Produces: `CollectionRange(start_month: str, end_month: str, start_date: str, end_date: str)`.
- Produces: `calculate_collection_range(today: date) -> CollectionRange`.

- [ ] **Step 1: Write the failing configuration tests**

Create `tests/__init__.py` as:

```python
"""Tests for the ToSuhyeon data collector."""
```

Create `tests/test_config.py` as:

```python
import tempfile
import unittest
from pathlib import Path

from collector.config import load_config
from collector.errors import CollectorError


class LoadConfigTests(unittest.TestCase):
    def test_reads_keys_from_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "# API keys\n"
                "\n"
                "FRED_API_KEY=fredtest123\n"
                "ECOS_API_KEY=ecostest456\n",
                encoding="utf-8",
            )

            config = load_config(env_path, environ={})

        self.assertEqual(config.fred_api_key, "fredtest123")
        self.assertEqual(config.ecos_api_key, "ecostest456")

    def test_environment_variables_work_without_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_env_path = Path(directory) / ".env"

            config = load_config(
                missing_env_path,
                environ={
                    "FRED_API_KEY": "fredfromgithub",
                    "ECOS_API_KEY": "ecosfromgithub",
                },
            )

        self.assertEqual(config.fred_api_key, "fredfromgithub")
        self.assertEqual(config.ecos_api_key, "ecosfromgithub")

    def test_environment_variables_override_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fredlocal\nECOS_API_KEY=ecoslocal\n",
                encoding="utf-8",
            )

            config = load_config(
                env_path,
                environ={
                    "FRED_API_KEY": "fredgithub",
                    "ECOS_API_KEY": "ecosgithub",
                },
            )

        self.assertEqual(config.fred_api_key, "fredgithub")
        self.assertEqual(config.ecos_api_key, "ecosgithub")

    def test_missing_key_names_variable_without_exposing_other_key(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fred-secret-that-must-not-appear\n",
                encoding="utf-8",
            )

            with self.assertRaises(CollectorError) as raised:
                load_config(env_path, environ={})

        message = str(raised.exception)
        self.assertIn("ECOS_API_KEY", message)
        self.assertNotIn("fred-secret-that-must-not-appear", message)

    def test_whitespace_in_key_is_rejected_without_showing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "FRED_API_KEY=fred secret\nECOS_API_KEY=ecostest456\n",
                encoding="utf-8",
            )

            with self.assertRaises(CollectorError) as raised:
                load_config(env_path, environ={})

        message = str(raised.exception)
        self.assertIn("FRED_API_KEY", message)
        self.assertNotIn("fred secret", message)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the configuration tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_config -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector'`.

- [ ] **Step 3: Implement the safe configuration loader**

Create `collector/__init__.py` as:

```python
"""Monthly ECOS and FRED data collector."""
```

Create `collector/errors.py` as:

```python
class CollectorError(Exception):
    """An error message that is safe to show without exposing secrets."""
```

Create `collector/config.py` as:

```python
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

from collector.errors import CollectorError


@dataclass(frozen=True)
class Config:
    fred_api_key: str
    ecos_api_key: str


def _read_env_file(env_path: Path) -> Dict[str, str]:
    if not env_path.is_file():
        return {}

    values: Dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise CollectorError(
            "수집 실패: .env 파일을 읽지 못했습니다. 파일 위치와 권한을 확인해주세요."
        ) from None

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "=" not in raw_line:
            raise CollectorError(
                f"수집 실패: .env 파일 {line_number}번째 줄에 '='이 없습니다."
            )
        raw_name, raw_value = raw_line.split("=", 1)
        name = raw_name.strip()
        if name:
            values[name] = raw_value
    return values


def _required_key(
    name: str,
    file_values: Mapping[str, str],
    environment: Mapping[str, str],
) -> str:
    value = environment.get(name, file_values.get(name, ""))
    if not value:
        raise CollectorError(
            f"수집 실패: {name}이 없습니다. .env 또는 GitHub Actions secrets를 확인해주세요."
        )
    if any(character.isspace() for character in value):
        raise CollectorError(
            f"수집 실패: {name}에 공백이 포함되어 있습니다. 키를 다시 붙여넣어 주세요."
        )
    return value


def load_config(
    env_path: Path,
    environ: Optional[Mapping[str, str]] = None,
) -> Config:
    environment = os.environ if environ is None else environ
    file_values = _read_env_file(env_path)
    return Config(
        fred_api_key=_required_key(
            "FRED_API_KEY",
            file_values,
            environment,
        ),
        ecos_api_key=_required_key(
            "ECOS_API_KEY",
            file_values,
            environment,
        ),
    )
```

Append the following lines to `.gitignore` while preserving its existing `.env` line:

```gitignore
__pycache__/
*.pyc
```

- [ ] **Step 4: Run the configuration tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_config -v
```

Expected: `Ran 5 tests` and `OK`.

- [ ] **Step 5: Write the failing date-range tests**

Create `tests/test_dates.py` as:

```python
import unittest
from datetime import date

from collector.dates import CollectionRange, calculate_collection_range


class CollectionRangeTests(unittest.TestCase):
    def test_calculates_inclusive_five_year_range(self):
        result = calculate_collection_range(date(2026, 7, 30))

        self.assertEqual(
            result,
            CollectionRange(
                start_month="202107",
                end_month="202607",
                start_date="2021-07-01",
                end_date="2026-07-30",
            ),
        )

    def test_handles_january_without_month_rollover(self):
        result = calculate_collection_range(date(2026, 1, 5))

        self.assertEqual(result.start_month, "202101")
        self.assertEqual(result.end_month, "202601")
        self.assertEqual(result.start_date, "2021-01-01")
        self.assertEqual(result.end_date, "2026-01-05")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run the date tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_dates -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector.dates'`.

- [ ] **Step 7: Implement the date-range calculation**

Create `collector/dates.py` as:

```python
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CollectionRange:
    start_month: str
    end_month: str
    start_date: str
    end_date: str


def calculate_collection_range(today: date) -> CollectionRange:
    start_year = today.year - 5
    return CollectionRange(
        start_month=f"{start_year:04d}{today.month:02d}",
        end_month=f"{today.year:04d}{today.month:02d}",
        start_date=f"{start_year:04d}-{today.month:02d}-01",
        end_date=today.isoformat(),
    )
```

- [ ] **Step 8: Run all foundation tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_config tests.test_dates -v
```

Expected: `Ran 7 tests` and `OK`.

- [ ] **Step 9: Commit the foundation**

Run:

```bash
git add .gitignore collector/__init__.py collector/errors.py collector/config.py collector/dates.py tests/__init__.py tests/test_config.py tests/test_dates.py
git commit -m "feat: add secure configuration and date range"
```

Expected: one commit containing only the listed foundation and test files.

---

### Task 2: FRED `WPU1017` Client and Parser

**Files:**
- Create: `collector/fred.py`
- Create: `tests/fixtures/fred_observations.json`
- Create: `tests/test_fred.py`

**Interfaces:**
- Consumes: `CollectorError`.
- Consumes: `CollectionRange`.
- Produces: `fetch_fred(api_key: str, date_range: CollectionRange, opener=urlopen) -> Tuple[Dict[str, object], str]`.
- Produces: `parse_fred(payload: Mapping[str, object]) -> Dict[str, Optional[str]]`.

- [ ] **Step 1: Add a representative FRED fixture**

Create `tests/fixtures/fred_observations.json` as:

```json
{
  "realtime_start": "2026-07-28",
  "realtime_end": "2026-07-28",
  "observation_start": "2026-05-01",
  "observation_end": "2026-06-30",
  "units": "lin",
  "sort_order": "asc",
  "observations": [
    {
      "realtime_start": "2026-07-28",
      "realtime_end": "2026-07-28",
      "date": "2026-05-01",
      "value": "359.100"
    },
    {
      "realtime_start": "2026-07-28",
      "realtime_end": "2026-07-28",
      "date": "2026-06-01",
      "value": "."
    }
  ]
}
```

- [ ] **Step 2: Write the failing FRED tests**

Create `tests/test_fred.py` as:

```python
import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from collector.dates import CollectionRange
from collector.errors import CollectorError
from collector.fred import fetch_fred, parse_fred


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fred_observations.json"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class FredTests(unittest.TestCase):
    def setUp(self):
        self.date_range = CollectionRange(
            start_month="202107",
            end_month="202607",
            start_date="2021-07-01",
            end_date="2026-07-30",
        )

    def test_fetch_builds_expected_request_and_returns_raw_text(self):
        captured = {}
        fixture_bytes = FIXTURE_PATH.read_bytes()

        def fake_opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return FakeResponse(fixture_bytes)

        payload, raw_text = fetch_fred(
            "fred-test-key",
            self.date_range,
            opener=fake_opener,
        )

        query = parse_qs(urlparse(captured["url"]).query)
        self.assertEqual(query["series_id"], ["WPU1017"])
        self.assertEqual(query["file_type"], ["json"])
        self.assertEqual(query["observation_start"], ["2021-07-01"])
        self.assertEqual(query["observation_end"], ["2026-07-30"])
        self.assertEqual(query["sort_order"], ["asc"])
        self.assertEqual(query["api_key"], ["fred-test-key"])
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(payload["observations"][0]["date"], "2026-05-01")
        self.assertEqual(raw_text, fixture_bytes.decode("utf-8"))

    def test_parse_keeps_numeric_text_and_marks_dot_as_missing(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        values = parse_fred(payload)

        self.assertEqual(
            values,
            {
                "2026-05": "359.100",
                "2026-06": None,
            },
        )

    def test_api_error_does_not_expose_provider_message(self):
        secret = "fred-secret-in-provider-message"
        body = json.dumps(
            {
                "error_code": 400,
                "error_message": f"invalid key {secret}",
            }
        ).encode("utf-8")

        with self.assertRaises(CollectorError) as raised:
            fetch_fred(
                secret,
                self.date_range,
                opener=lambda url, timeout: FakeResponse(body),
            )

        message = str(raised.exception)
        self.assertIn("FRED", message)
        self.assertIn("400", message)
        self.assertNotIn(secret, message)

    def test_invalid_numeric_value_is_rejected(self):
        payload = {
            "observations": [
                {
                    "date": "2026-06-01",
                    "value": "not-a-number",
                }
            ]
        }

        with self.assertRaisesRegex(CollectorError, "숫자"):
            parse_fred(payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the FRED tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_fred -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector.fred'`.

- [ ] **Step 4: Implement the FRED client and parser**

Create `collector/fred.py` as:

```python
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, Mapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from collector.dates import CollectionRange
from collector.errors import CollectorError


FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred(
    api_key: str,
    date_range: CollectionRange,
    opener: Callable = urlopen,
) -> Tuple[Dict[str, object], str]:
    query = urlencode(
        {
            "series_id": "WPU1017",
            "file_type": "json",
            "observation_start": date_range.start_date,
            "observation_end": date_range.end_date,
            "sort_order": "asc",
            "api_key": api_key,
        }
    )
    request_url = f"{FRED_URL}?{query}"

    try:
        with opener(request_url, timeout=30) as response:
            raw_bytes = response.read()
    except HTTPError as error:
        raise CollectorError(
            f"수집 실패: FRED 서버가 HTTP {error.code} 오류를 반환했습니다."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise CollectorError(
            "수집 실패: FRED에 연결하지 못했습니다. 인터넷 연결 후 다시 실행해주세요."
        ) from None

    try:
        raw_text = raw_bytes.decode("utf-8")
        payload = json.loads(raw_text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CollectorError(
            "수집 실패: FRED 응답이 올바른 JSON 형식이 아닙니다."
        ) from None

    if not isinstance(payload, dict):
        raise CollectorError("수집 실패: FRED 응답 구조가 올바르지 않습니다.")
    if "error_code" in payload:
        error_code = str(payload.get("error_code", "알 수 없음"))
        raise CollectorError(
            f"수집 실패: FRED가 오류 코드 {error_code}를 반환했습니다."
        )
    return payload, raw_text


def parse_fred(
    payload: Mapping[str, object],
) -> Dict[str, Optional[str]]:
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise CollectorError(
            "수집 실패: FRED 응답에 observations 목록이 없습니다."
        )

    values: Dict[str, Optional[str]] = {}
    for observation in observations:
        if not isinstance(observation, dict):
            raise CollectorError(
                "수집 실패: FRED 관측값 구조가 올바르지 않습니다."
            )
        raw_date = observation.get("date")
        raw_value = observation.get("value")
        if not isinstance(raw_date, str) or not isinstance(raw_value, str):
            raise CollectorError(
                "수집 실패: FRED 관측값의 날짜 또는 값이 없습니다."
            )
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            raise CollectorError(
                "수집 실패: FRED 날짜 형식이 올바르지 않습니다."
            ) from None

        month = parsed_date.strftime("%Y-%m")
        if raw_value == ".":
            values[month] = None
            continue
        try:
            Decimal(raw_value)
        except InvalidOperation:
            raise CollectorError(
                f"수집 실패: FRED {month} 값이 숫자가 아닙니다."
            ) from None
        values[month] = raw_value

    if not values or not any(value is not None for value in values.values()):
        raise CollectorError(
            "수집 실패: FRED에서 사용할 수 있는 월별 값을 받지 못했습니다."
        )
    return values
```

- [ ] **Step 5: Run the FRED tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_fred -v
```

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 6: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 11 tests` and `OK`.

- [ ] **Step 7: Commit the FRED client**

Run:

```bash
git add collector/fred.py tests/fixtures/fred_observations.json tests/test_fred.py
git commit -m "feat: collect monthly FRED steel PPI"
```

Expected: one commit containing only the FRED client, fixture, and tests.

---

### Task 3: ECOS `722Y001 / 0101000` Client and Parser

**Files:**
- Create: `collector/ecos.py`
- Create: `tests/fixtures/ecos_base_rate.json`
- Create: `tests/test_ecos.py`

**Interfaces:**
- Consumes: `CollectorError`.
- Consumes: `CollectionRange`.
- Produces: `fetch_ecos(api_key: str, date_range: CollectionRange, opener=urlopen) -> Tuple[Dict[str, object], str]`.
- Produces: `parse_ecos(payload: Mapping[str, object]) -> Dict[str, Optional[str]]`.

- [ ] **Step 1: Add a representative ECOS fixture**

Create `tests/fixtures/ecos_base_rate.json` as:

```json
{
  "StatisticSearch": {
    "list_total_count": 2,
    "row": [
      {
        "STAT_CODE": "722Y001",
        "STAT_NAME": "1.3.1. 한국은행 기준금리 및 여수신금리",
        "ITEM_CODE1": "0101000",
        "ITEM_NAME1": "한국은행 기준금리",
        "ITEM_CODE2": null,
        "ITEM_NAME2": null,
        "ITEM_CODE3": null,
        "ITEM_NAME3": null,
        "ITEM_CODE4": null,
        "ITEM_NAME4": null,
        "UNIT_NAME": "연%",
        "WGT": null,
        "TIME": "202605",
        "DATA_VALUE": "2.5"
      },
      {
        "STAT_CODE": "722Y001",
        "STAT_NAME": "1.3.1. 한국은행 기준금리 및 여수신금리",
        "ITEM_CODE1": "0101000",
        "ITEM_NAME1": "한국은행 기준금리",
        "ITEM_CODE2": null,
        "ITEM_NAME2": null,
        "ITEM_CODE3": null,
        "ITEM_NAME3": null,
        "ITEM_CODE4": null,
        "ITEM_NAME4": null,
        "UNIT_NAME": "연%",
        "WGT": null,
        "TIME": "202606",
        "DATA_VALUE": "2.5"
      }
    ]
  }
}
```

- [ ] **Step 2: Write the failing ECOS tests**

Create `tests/test_ecos.py` as:

```python
import json
import unittest
from pathlib import Path

from collector.dates import CollectionRange
from collector.ecos import fetch_ecos, parse_ecos
from collector.errors import CollectorError


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ecos_base_rate.json"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class EcosTests(unittest.TestCase):
    def setUp(self):
        self.date_range = CollectionRange(
            start_month="202107",
            end_month="202607",
            start_date="2021-07-01",
            end_date="2026-07-30",
        )

    def test_fetch_builds_expected_request_and_returns_raw_text(self):
        captured = {}
        fixture_bytes = FIXTURE_PATH.read_bytes()

        def fake_opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return FakeResponse(fixture_bytes)

        payload, raw_text = fetch_ecos(
            "ecos-test-key",
            self.date_range,
            opener=fake_opener,
        )

        self.assertIn(
            "/StatisticSearch/ecos-test-key/json/kr/1/1000/"
            "722Y001/M/202107/202607/0101000",
            captured["url"],
        )
        self.assertEqual(captured["timeout"], 30)
        self.assertEqual(
            payload["StatisticSearch"]["row"][0]["ITEM_CODE1"],
            "0101000",
        )
        self.assertEqual(raw_text, fixture_bytes.decode("utf-8"))

    def test_parse_returns_monthly_base_rate(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        values = parse_ecos(payload)

        self.assertEqual(
            values,
            {
                "2026-05": "2.5",
                "2026-06": "2.5",
            },
        )

    def test_provider_error_does_not_expose_provider_message(self):
        secret = "ecos-secret-in-provider-message"
        payload = {
            "RESULT": {
                "CODE": "INFO-100",
                "MESSAGE": f"invalid key {secret}",
            }
        }

        with self.assertRaises(CollectorError) as raised:
            parse_ecos(payload)

        message = str(raised.exception)
        self.assertIn("ECOS", message)
        self.assertIn("INFO-100", message)
        self.assertNotIn(secret, message)

    def test_unexpected_item_code_is_rejected(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["StatisticSearch"]["row"][0]["ITEM_CODE1"] = "WRONG"

        with self.assertRaisesRegex(CollectorError, "항목"):
            parse_ecos(payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the ECOS tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_ecos -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector.ecos'`.

- [ ] **Step 4: Implement the ECOS client and parser**

Create `collector/ecos.py` as:

```python
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, Mapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from collector.dates import CollectionRange
from collector.errors import CollectorError


ECOS_BASE_URL = "https://ecos.bok.or.kr/api"
ECOS_STAT_CODE = "722Y001"
ECOS_ITEM_CODE = "0101000"


def _raise_for_provider_error(payload: Mapping[str, object]) -> None:
    result = payload.get("RESULT")
    if not isinstance(result, dict):
        return
    error_code = str(result.get("CODE", "알 수 없음"))
    raise CollectorError(
        f"수집 실패: ECOS가 오류 코드 {error_code}를 반환했습니다."
    )


def fetch_ecos(
    api_key: str,
    date_range: CollectionRange,
    opener: Callable = urlopen,
) -> Tuple[Dict[str, object], str]:
    safe_key = quote(api_key, safe="")
    request_url = (
        f"{ECOS_BASE_URL}/StatisticSearch/{safe_key}/json/kr/1/1000/"
        f"{ECOS_STAT_CODE}/M/{date_range.start_month}/"
        f"{date_range.end_month}/{ECOS_ITEM_CODE}"
    )

    try:
        with opener(request_url, timeout=30) as response:
            raw_bytes = response.read()
    except HTTPError as error:
        raise CollectorError(
            f"수집 실패: ECOS 서버가 HTTP {error.code} 오류를 반환했습니다."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise CollectorError(
            "수집 실패: ECOS에 연결하지 못했습니다. 인터넷 연결 후 다시 실행해주세요."
        ) from None

    try:
        raw_text = raw_bytes.decode("utf-8")
        payload = json.loads(raw_text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CollectorError(
            "수집 실패: ECOS 응답이 올바른 JSON 형식이 아닙니다."
        ) from None

    if not isinstance(payload, dict):
        raise CollectorError("수집 실패: ECOS 응답 구조가 올바르지 않습니다.")
    _raise_for_provider_error(payload)
    return payload, raw_text


def parse_ecos(
    payload: Mapping[str, object],
) -> Dict[str, Optional[str]]:
    _raise_for_provider_error(payload)
    statistic_search = payload.get("StatisticSearch")
    if not isinstance(statistic_search, dict):
        raise CollectorError(
            "수집 실패: ECOS 응답에 StatisticSearch가 없습니다."
        )
    rows = statistic_search.get("row")
    if not isinstance(rows, list):
        raise CollectorError(
            "수집 실패: ECOS 응답에 기준금리 목록이 없습니다."
        )

    values: Dict[str, Optional[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise CollectorError(
                "수집 실패: ECOS 기준금리 행 구조가 올바르지 않습니다."
            )
        if (
            row.get("STAT_CODE") != ECOS_STAT_CODE
            or row.get("ITEM_CODE1") != ECOS_ITEM_CODE
            or row.get("UNIT_NAME") != "연%"
        ):
            raise CollectorError(
                "수집 실패: ECOS 기준금리 통계표 또는 항목이 예상과 다릅니다."
            )

        raw_time = row.get("TIME")
        raw_value = row.get("DATA_VALUE")
        if not isinstance(raw_time, str):
            raise CollectorError(
                "수집 실패: ECOS 기준금리 날짜가 없습니다."
            )
        try:
            parsed_month = datetime.strptime(raw_time, "%Y%m")
        except ValueError:
            raise CollectorError(
                "수집 실패: ECOS 기준금리 날짜 형식이 올바르지 않습니다."
            ) from None

        month = parsed_month.strftime("%Y-%m")
        if raw_value in (None, "", "."):
            values[month] = None
            continue
        if not isinstance(raw_value, str):
            raise CollectorError(
                f"수집 실패: ECOS {month} 기준금리 값이 문자열이 아닙니다."
            )
        try:
            Decimal(raw_value)
        except InvalidOperation:
            raise CollectorError(
                f"수집 실패: ECOS {month} 기준금리 값이 숫자가 아닙니다."
            ) from None
        values[month] = raw_value

    if not values or not any(value is not None for value in values.values()):
        raise CollectorError(
            "수집 실패: ECOS에서 사용할 수 있는 월별 기준금리를 받지 못했습니다."
        )
    return values
```

- [ ] **Step 5: Run the ECOS tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_ecos -v
```

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 6: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 15 tests` and `OK`.

- [ ] **Step 7: Commit the ECOS client**

Run:

```bash
git add collector/ecos.py tests/fixtures/ecos_base_rate.json tests/test_ecos.py
git commit -m "feat: collect monthly ECOS base rate"
```

Expected: one commit containing only the ECOS client, fixture, and tests.

---

### Task 4: Monthly Merge and Atomic Storage

**Files:**
- Create: `collector/transform.py`
- Create: `collector/storage.py`
- Create: `tests/test_transform.py`
- Create: `tests/test_storage.py`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`

**Interfaces:**
- Consumes: `CollectorError`.
- Produces: `merge_monthly(ecos_values: Mapping[str, Optional[str]], fred_values: Mapping[str, Optional[str]]) -> List[Dict[str, str]]`.
- Produces: `save_raw_response(raw_dir: Path, source: str, raw_text: str, secrets: Sequence[str], run_id: str) -> Path`.
- Produces: `save_csv(output_path: Path, rows: Sequence[Mapping[str, str]]) -> Path`.

- [ ] **Step 1: Write the failing monthly-merge tests**

Create `tests/test_transform.py` as:

```python
import unittest

from collector.errors import CollectorError
from collector.transform import merge_monthly


class MergeMonthlyTests(unittest.TestCase):
    def test_merges_month_union_in_chronological_order(self):
        ecos_values = {
            "2026-05": "2.5",
            "2026-06": "2.5",
        }
        fred_values = {
            "2026-04": "355.2",
            "2026-05": "359.100",
        }

        rows = merge_monthly(ecos_values, fred_values)

        self.assertEqual(
            rows,
            [
                {
                    "month": "2026-04",
                    "korea_base_rate_percent": "",
                    "us_steel_ppi_index": "355.2",
                },
                {
                    "month": "2026-05",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "359.100",
                },
                {
                    "month": "2026-06",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "",
                },
            ],
        )

    def test_none_becomes_empty_csv_value(self):
        rows = merge_monthly(
            {"2026-06": None},
            {"2026-06": "361.439"},
        )

        self.assertEqual(rows[0]["korea_base_rate_percent"], "")
        self.assertEqual(rows[0]["us_steel_ppi_index"], "361.439")

    def test_empty_inputs_are_rejected(self):
        with self.assertRaises(CollectorError):
            merge_monthly({}, {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the merge tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_transform -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector.transform'`.

- [ ] **Step 3: Implement the monthly merge**

Create `collector/transform.py` as:

```python
from typing import Dict, List, Mapping, Optional

from collector.errors import CollectorError


def merge_monthly(
    ecos_values: Mapping[str, Optional[str]],
    fred_values: Mapping[str, Optional[str]],
) -> List[Dict[str, str]]:
    months = sorted(set(ecos_values) | set(fred_values))
    if not months:
        raise CollectorError(
            "수집 실패: CSV로 합칠 월별 데이터가 없습니다."
        )

    rows: List[Dict[str, str]] = []
    for month in months:
        rows.append(
            {
                "month": month,
                "korea_base_rate_percent": ecos_values.get(month) or "",
                "us_steel_ppi_index": fred_values.get(month) or "",
            }
        )
    return rows
```

- [ ] **Step 4: Run the merge tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_transform -v
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 5: Write the failing storage tests**

Create `tests/test_storage.py` as:

```python
import codecs
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collector.errors import CollectorError
from collector.storage import save_csv, save_raw_response


class StorageTests(unittest.TestCase):
    def test_saves_raw_response_with_deterministic_name(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"

            output_path = save_raw_response(
                raw_dir=raw_dir,
                source="fred",
                raw_text='{"observations": []}',
                secrets=("fred-secret", "ecos-secret"),
                run_id="20260730T020000Z",
            )

            self.assertEqual(
                output_path.name,
                "fred_WPU1017_20260730T020000Z.json",
            )
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                '{"observations": []}',
            )

    def test_refuses_to_store_a_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"

            with self.assertRaisesRegex(CollectorError, "비밀 키"):
                save_raw_response(
                    raw_dir=raw_dir,
                    source="ecos",
                    raw_text='{"message": "ecos-secret"}',
                    secrets=("fred-secret", "ecos-secret"),
                    run_id="20260730T020000Z",
                )

            self.assertFalse(raw_dir.exists())

    def test_csv_has_bom_header_and_missing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "monthly_indicators.csv"
            rows = [
                {
                    "month": "2026-06",
                    "korea_base_rate_percent": "2.5",
                    "us_steel_ppi_index": "",
                }
            ]

            save_csv(output_path, rows)

            raw_bytes = output_path.read_bytes()
            self.assertTrue(raw_bytes.startswith(codecs.BOM_UTF8))
            self.assertEqual(
                raw_bytes.decode("utf-8-sig"),
                "month,korea_base_rate_percent,us_steel_ppi_index\r\n"
                "2026-06,2.5,\r\n",
            )

    def test_failed_replace_preserves_existing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "monthly_indicators.csv"
            output_path.write_text("old-data\n", encoding="utf-8")

            with patch(
                "collector.storage.os.replace",
                side_effect=OSError("disk error"),
            ):
                with self.assertRaises(CollectorError):
                    save_csv(
                        output_path,
                        [
                            {
                                "month": "2026-06",
                                "korea_base_rate_percent": "2.5",
                                "us_steel_ppi_index": "361.439",
                            }
                        ],
                    )

            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "old-data\n",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run the storage tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_storage -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collector.storage'`.

- [ ] **Step 7: Implement atomic raw and CSV storage**

Create `collector/storage.py` as:

```python
import csv
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, Mapping, Optional, Sequence, TextIO

from collector.errors import CollectorError


CSV_FIELDS = (
    "month",
    "korea_base_rate_percent",
    "us_steel_ppi_index",
)
RAW_PREFIXES = {
    "fred": "fred_WPU1017",
    "ecos": "ecos_base_rate",
}


def _atomic_text_write(
    target: Path,
    write_content: Callable[[TextIO], None],
    encoding: str,
    newline: Optional[str] = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline=newline,
            dir=str(target.parent),
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            write_content(temporary_file)
        os.replace(str(temporary_path), str(target))
    except (OSError, UnicodeError, ValueError, csv.Error):
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise CollectorError(
            f"수집 실패: {target.name} 파일을 안전하게 저장하지 못했습니다."
        ) from None


def save_raw_response(
    raw_dir: Path,
    source: str,
    raw_text: str,
    secrets: Sequence[str],
    run_id: str,
) -> Path:
    prefix = RAW_PREFIXES.get(source)
    if prefix is None:
        raise CollectorError(
            "수집 실패: 알 수 없는 원본 데이터 출처입니다."
        )
    if any(secret and secret in raw_text for secret in secrets):
        raise CollectorError(
            "수집 실패: 원본 응답에 비밀 키가 포함되어 저장을 중단했습니다."
        )
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise CollectorError(
            "수집 실패: 올바른 JSON만 원본으로 저장할 수 있습니다."
        ) from None
    if not isinstance(parsed, dict):
        raise CollectorError(
            "수집 실패: JSON 원본의 최상위 구조가 객체가 아닙니다."
        )

    target = raw_dir / f"{prefix}_{run_id}.json"
    _atomic_text_write(
        target,
        lambda handle: handle.write(raw_text),
        encoding="utf-8",
    )
    return target


def save_csv(
    output_path: Path,
    rows: Sequence[Mapping[str, str]],
) -> Path:
    if not rows:
        raise CollectorError(
            "수집 실패: 저장할 월별 CSV 행이 없습니다."
        )

    def write_rows(handle: TextIO) -> None:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)

    _atomic_text_write(
        output_path,
        write_rows,
        encoding="utf-8-sig",
        newline="",
    )
    return output_path
```

Create `data/raw/.gitkeep` as:

```text
# Keep this generated raw-data directory in Git.
```

Create `data/processed/.gitkeep` as:

```text
# Keep this generated processed-data directory in Git.
```

- [ ] **Step 8: Run the transform and storage tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_transform tests.test_storage -v
```

Expected: `Ran 7 tests` and `OK`.

- [ ] **Step 9: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 22 tests` and `OK`.

- [ ] **Step 10: Commit transform and storage**

Run:

```bash
git add collector/transform.py collector/storage.py tests/test_transform.py tests/test_storage.py data/raw/.gitkeep data/processed/.gitkeep
git commit -m "feat: merge and store monthly indicators"
```

Expected: one commit containing only merge, storage, tests, and data-directory markers.

---

### Task 5: Beginner-Facing Collection CLI

**Files:**
- Create: `collect_data.py`
- Create: `tests/test_collect_data.py`

**Interfaces:**
- Consumes: all interfaces from Tasks 1–4.
- Produces: `run(project_root: Path, today: Optional[date] = None, now: Optional[datetime] = None) -> int`.
- Produces: `main() -> int`.

- [ ] **Step 1: Write the failing CLI tests**

Create `tests/test_collect_data.py` as:

```python
import io
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import collect_data
from collector.config import Config
from collector.dates import CollectionRange
from collector.errors import CollectorError


class CollectDataTests(unittest.TestCase):
    def test_run_orchestrates_both_sources_and_saves_outputs(self):
        project_root = Path("/tmp/tosuhyeon-test")
        date_range = CollectionRange(
            start_month="202107",
            end_month="202607",
            start_date="2021-07-01",
            end_date="2026-07-30",
        )
        fred_payload = {"observations": []}
        ecos_payload = {"StatisticSearch": {"row": []}}
        fred_values = {"2026-06": "361.439"}
        ecos_values = {"2026-06": "2.5"}
        merged_rows = [
            {
                "month": "2026-06",
                "korea_base_rate_percent": "2.5",
                "us_steel_ppi_index": "361.439",
            }
        ]

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "collect_data.load_config",
                    return_value=Config("fred-secret", "ecos-secret"),
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.calculate_collection_range",
                    return_value=date_range,
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.fetch_fred",
                    return_value=(fred_payload, '{"observations": []}'),
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.parse_fred",
                    return_value=fred_values,
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.fetch_ecos",
                    return_value=(
                        ecos_payload,
                        '{"StatisticSearch": {"row": []}}',
                    ),
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.parse_ecos",
                    return_value=ecos_values,
                )
            )
            stack.enter_context(
                patch(
                    "collect_data.merge_monthly",
                    return_value=merged_rows,
                )
            )
            save_raw = stack.enter_context(
                patch(
                    "collect_data.save_raw_response",
                    side_effect=[
                        project_root / "data/raw/fred.json",
                        project_root / "data/raw/ecos.json",
                    ],
                )
            )
            save_csv = stack.enter_context(
                patch(
                    "collect_data.save_csv",
                    return_value=project_root
                    / "data/processed/monthly_indicators.csv",
                )
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = collect_data.run(
                    project_root,
                    today=date(2026, 7, 30),
                    now=datetime(2026, 7, 30, 2, 0, tzinfo=timezone.utc),
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(save_raw.call_count, 2)
        save_csv.assert_called_once_with(
            project_root / "data/processed/monthly_indicators.csv",
            merged_rows,
        )
        text = output.getvalue()
        self.assertIn("[1/4]", text)
        self.assertIn("FRED 철강 PPI 1건", text)
        self.assertIn("ECOS 기준금리 1건", text)
        self.assertIn("monthly_indicators.csv", text)
        self.assertNotIn("fred-secret", text)
        self.assertNotIn("ecos-secret", text)

    def test_main_returns_one_and_prints_safe_error(self):
        error_output = io.StringIO()
        with patch(
            "collect_data.run",
            side_effect=CollectorError("수집 실패: 안전한 오류"),
        ):
            with redirect_stderr(error_output):
                exit_code = collect_data.main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(error_output.getvalue(), "수집 실패: 안전한 오류\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the CLI tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_collect_data -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'collect_data'`.

- [ ] **Step 3: Implement the collection CLI**

Create `collect_data.py` as:

```python
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from collector.config import load_config
from collector.dates import calculate_collection_range
from collector.ecos import fetch_ecos, parse_ecos
from collector.errors import CollectorError
from collector.fred import fetch_fred, parse_fred
from collector.storage import save_csv, save_raw_response
from collector.transform import merge_monthly


def run(
    project_root: Path,
    today: Optional[date] = None,
    now: Optional[datetime] = None,
) -> int:
    config = load_config(project_root / ".env")
    print("[1/4] API 키를 확인했습니다.")

    collection_date = date.today() if today is None else today
    date_range = calculate_collection_range(collection_date)
    run_moment = datetime.now(timezone.utc) if now is None else now
    if run_moment.tzinfo is None:
        run_moment = run_moment.replace(tzinfo=timezone.utc)
    run_id = run_moment.astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    secrets = (config.fred_api_key, config.ecos_api_key)
    raw_dir = project_root / "data" / "raw"

    fred_payload, fred_raw = fetch_fred(
        config.fred_api_key,
        date_range,
    )
    fred_values = parse_fred(fred_payload)
    save_raw_response(
        raw_dir=raw_dir,
        source="fred",
        raw_text=fred_raw,
        secrets=secrets,
        run_id=run_id,
    )
    print(f"[2/4] FRED 철강 PPI {len(fred_values)}건을 수집했습니다.")

    ecos_payload, ecos_raw = fetch_ecos(
        config.ecos_api_key,
        date_range,
    )
    ecos_values = parse_ecos(ecos_payload)
    save_raw_response(
        raw_dir=raw_dir,
        source="ecos",
        raw_text=ecos_raw,
        secrets=secrets,
        run_id=run_id,
    )
    print(f"[3/4] ECOS 기준금리 {len(ecos_values)}건을 수집했습니다.")

    rows = merge_monthly(ecos_values, fred_values)
    output_path = save_csv(
        project_root / "data" / "processed" / "monthly_indicators.csv",
        rows,
    )
    print(f"[4/4] 월별 CSV {len(rows)}행을 저장했습니다.")
    print(f"완료: {output_path.relative_to(project_root)}")
    return 0


def main() -> int:
    project_root = Path(__file__).resolve().parent
    try:
        return run(project_root)
    except CollectorError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the CLI tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_collect_data -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 24 tests` and `OK`.

- [ ] **Step 6: Compile every Python file**

Run:

```bash
python3 -m compileall -q collect_data.py collector tests
```

Expected: exit code `0` and no output.

- [ ] **Step 7: Commit the CLI**

Run:

```bash
git add collect_data.py tests/test_collect_data.py
git commit -m "feat: add beginner data collection command"
```

Expected: one commit containing the CLI and its orchestration tests.

---

### Task 6: Weekly GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/collect-weekly.yml`
- Create: `tests/test_workflow.py`

**Interfaces:**
- Consumes: `python3 -m unittest discover -s tests -v`.
- Consumes: `python3 collect_data.py`.
- Consumes: GitHub secrets `FRED_API_KEY` and `ECOS_API_KEY`.
- Produces: Monday 11:00 Asia/Seoul schedule and manual `workflow_dispatch`.
- Produces: data-only commit to `main` using repository-scoped `GITHUB_TOKEN`.

- [ ] **Step 1: Write the failing workflow contract test**

Create `tests/test_workflow.py` as:

```python
import unittest
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "workflows"
    / "collect-weekly.yml"
)


class WorkflowContractTests(unittest.TestCase):
    def test_workflow_has_schedule_secrets_and_minimal_commit_scope(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn('cron: "0 11 * * 1"', text)
        self.assertIn('timezone: "Asia/Seoul"', text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: write", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn(
            "FRED_API_KEY: ${{ secrets.FRED_API_KEY }}",
            text,
        )
        self.assertIn(
            "ECOS_API_KEY: ${{ secrets.ECOS_API_KEY }}",
            text,
        )
        self.assertIn(
            "git add -- data/raw "
            "data/processed/monthly_indicators.csv",
            text,
        )
        self.assertNotIn("git add .", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the workflow contract test and verify RED**

Run:

```bash
python3 -m unittest tests.test_workflow -v
```

Expected: `ERROR` with `FileNotFoundError` for `collect-weekly.yml`.

- [ ] **Step 3: Implement the weekly workflow**

Create `.github/workflows/collect-weekly.yml` as:

```yaml
name: Collect weekly economic data

on:
  schedule:
    - cron: "0 11 * * 1"
      timezone: "Asia/Seoul"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: weekly-economic-data
  cancel-in-progress: false

jobs:
  collect:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Check out repository
        uses: actions/checkout@v6
        with:
          ref: main

      - name: Set up Python 3.9
        uses: actions/setup-python@v6
        with:
          python-version: "3.9"

      - name: Run tests
        run: python3 -m unittest discover -s tests -v

      - name: Collect ECOS and FRED data
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          ECOS_API_KEY: ${{ secrets.ECOS_API_KEY }}
        run: python3 collect_data.py

      - name: Commit generated data
        shell: bash
        run: |
          set -euo pipefail
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -- data/raw data/processed/monthly_indicators.csv
          if git diff --cached --quiet; then
            echo "No generated data changed."
            exit 0
          fi
          git commit -m "data: collect weekly indicators $(date -u +'%Y-%m-%d')"
          git push origin HEAD:main
```

- [ ] **Step 4: Run the workflow contract test and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workflow -v
```

Expected: `Ran 1 test` and `OK`.

- [ ] **Step 5: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 25 tests` and `OK`.

- [ ] **Step 6: Inspect the workflow for secret and staging safety**

Run:

```bash
rg -n 'pull_request|git add \.|api_key=|StatisticSearch/.+/json' .github/workflows/collect-weekly.yml
```

Expected: no output and exit code `1`; the workflow contains none of those unsafe patterns.

- [ ] **Step 7: Commit the workflow**

Run:

```bash
git add .github/workflows/collect-weekly.yml tests/test_workflow.py
git commit -m "feat: automate weekly economic data collection"
```

Expected: one commit containing only the workflow and its contract test.

---

### Task 7: Beginner README

**Files:**
- Modify: `README.md`
- Create: `tests/test_readme.py`

**Interfaces:**
- Consumes: the local command, data paths, workflow, secret names, and failure behavior from Tasks 1–6.
- Produces: one beginner path from “What is GitHub?” through local execution and GitHub Actions verification.

- [ ] **Step 1: Write the failing README contract test**

Create `tests/test_readme.py` as:

```python
import unittest
from pathlib import Path


README_PATH = Path(__file__).parents[1] / "README.md"


class ReadmeContractTests(unittest.TestCase):
    def test_readme_contains_beginner_local_and_github_instructions(self):
        text = README_PATH.read_text(encoding="utf-8")
        required_phrases = (
            "python3 collect_data.py",
            "python3 -m unittest discover -s tests -v",
            "data/raw",
            "data/processed/monthly_indicators.csv",
            "FRED_API_KEY",
            "ECOS_API_KEY",
            "suhyeonhong-bit/ToSuhyeon",
            "매주 월요일 오전 11시",
            "Run workflow",
            "Actions secrets",
            "자동으로 GitHub에 올라가지 않습니다",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the README contract test and verify RED**

Run:

```bash
python3 -m unittest tests.test_readme -v
```

Expected: `FAIL`; the existing README does not yet contain the complete local and GitHub instructions.

- [ ] **Step 3: Append the beginner operation guide to README**

Append this exact section to `README.md`:

````markdown

## 직접 만드는 첫 데이터 수집기

이 저장소에는 한국은행 기준금리와 미국 철강 생산자물가지수를 가져오는
작은 Python 프로그램이 들어 있습니다.

프로그램이 하는 일은 다음과 같습니다.

1. ECOS에서 한국은행 기준금리를 가져옵니다.
2. FRED에서 미국 철강 PPI(`WPU1017`)를 가져옵니다.
3. 기관이 보낸 원본 JSON을 `data/raw`에 보관합니다.
4. 두 지표를 월별로 합친 CSV를
   `data/processed/monthly_indicators.csv`에 저장합니다.

### 먼저 알아둘 용어

- **GitHub**: 인터넷에 있는 프로젝트 보관함입니다.
- **저장소(repository)**: 프로젝트 파일과 변경 기록을 함께 보관하는
  공간입니다.
- **commit**: 파일이 바뀐 상태를 하나의 기록으로 남기는 일입니다.
- **fork**: 다른 사람의 공개 저장소를 내 GitHub 계정으로 복사하는
  기능입니다.
- **GitHub Actions**: GitHub가 정해진 명령을 대신 실행해주는 임시
  컴퓨터입니다.

이 프로젝트의 자동화 저장소는 공개 fork인
`suhyeonhong-bit/ToSuhyeon`입니다. 원본 `yealu/ToSuhyeon`에는 자동
수집 결과를 쓰지 않습니다.

### 내 Mac에서 직접 실행하기

VS Code에서 `/Users/suhyeonhong/Documents/GitHub/ToSuhyeon` 폴더를
열고 터미널에서 다음 명령을 실행합니다.

```bash
python3 collect_data.py
```

실행하면 `[1/4]`부터 `[4/4]`까지 진행 상황이 보입니다. `완료:`가 나오면
다음 파일을 확인합니다.

- `data/raw/fred_WPU1017_날짜와시간.json`
- `data/raw/ecos_base_rate_날짜와시간.json`
- `data/processed/monthly_indicators.csv`

JSON은 기관에서 받은 원본이고, CSV는 사람이 표로 보기 좋게 합친
결과입니다. 발표가 아직 안 된 월은 오류가 아니라 빈칸으로 표시될 수
있습니다.

로컬 실행 전에 프로젝트의 `.env`에는 아래 이름의 두 키가 있어야 합니다.

```text
FRED_API_KEY=직접_발급받은_키
ECOS_API_KEY=직접_발급받은_키
```

실제 키는 이 README, 코드, 채팅창에 입력하지 마세요. `.env`는 Git에서
제외되어 있습니다.

프로그램 검사는 다음 명령으로 실행합니다.

```bash
python3 -m unittest discover -s tests -v
```

마지막에 `OK`가 나오면 자동 검사에 통과한 것입니다.

내 Mac에서 프로그램을 실행해 생긴 데이터는 자동으로 GitHub에 올라가지 않습니다.
GitHub에 보내려면 별도의 commit과 push가 필요합니다.

### GitHub에서 매주 자동 실행하기

GitHub Actions는 매주 월요일 오전 11시 한국 시간에 같은 프로그램을
실행합니다. GitHub 서버 사정에 따라 시작이 몇 분 늦을 수 있습니다.

GitHub는 내 Mac의 `.env`를 볼 수 없으므로 수현님 저장소에 두 개의
Actions secrets를 한 번 등록해야 합니다.

1. GitHub에서 `suhyeonhong-bit/ToSuhyeon` 저장소를 엽니다.
2. `Settings`를 누릅니다.
3. `Secrets and variables` → `Actions`로 이동합니다.
4. `New repository secret`을 눌러 `FRED_API_KEY`를 등록합니다.
5. 다시 `New repository secret`을 눌러 `ECOS_API_KEY`를 등록합니다.

키 값은 GitHub 입력란에 직접 붙여넣고 채팅창에는 보내지 마세요. 저장된
secret 값은 다시 화면에 표시되지 않습니다.

처음에는 예약 시간을 기다리지 않고 직접 시험합니다.

1. 저장소 위쪽의 `Actions`를 누릅니다.
2. fork의 워크플로 활성화 안내가 보이면 내용을 확인하고 활성화 버튼을
   누릅니다.
3. 왼쪽에서 `Collect weekly economic data`를 선택합니다.
4. `Run workflow` → 초록색 `Run workflow`를 누릅니다.
5. 실행 기록의 표시가 초록색 체크가 될 때까지 기다립니다.

성공하면 새 원본 JSON 두 개와 최신 CSV가 자동 commit됩니다. 실패하면
빨간색 `X`가 표시되고 이전 데이터는 그대로 유지됩니다.

공개 저장소에서 오랫동안 아무 활동도 없으면 GitHub가 예약 워크플로를
비활성화할 수 있습니다. 정상적인 주간 데이터 commit이 계속되면 활동도
이어집니다. 실패가 장기간 계속되면 `Actions` 화면에서 워크플로가
활성화되어 있는지 확인합니다.

### 자주 만나는 오류

- `FRED_API_KEY` 또는 `ECOS_API_KEY` 오류: 키 이름과 저장 위치를
  확인합니다. 키 값은 채팅에 보내지 않습니다.
- 연결 오류: 인터넷 연결을 확인하고 다시 실행합니다.
- GitHub Actions 실패: 실패한 실행을 눌러 어느 단계에 빨간 표시가
  있는지 확인합니다.
- 최신 월이 빈칸: 기관의 발표 시차일 수 있으므로 다음 실행에서 다시
  확인합니다.
````

- [ ] **Step 4: Run the README contract test and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_readme -v
```

Expected: `Ran 1 test` and `OK`.

- [ ] **Step 5: Run the complete test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 26 tests` and `OK`.

- [ ] **Step 6: Verify beginner commands and secret warnings are visible**

Run:

```bash
rg -n 'python3 collect_data.py|Actions secrets|Run workflow|채팅창|자동으로 GitHub에 올라가지 않습니다' README.md
```

Expected: matches for every phrase in the appended beginner guide.

- [ ] **Step 7: Commit the beginner documentation**

Run:

```bash
git add README.md tests/test_readme.py
git commit -m "docs: explain local and GitHub data collection"
```

Expected: one commit containing the README guide and its contract test.

---

### Task 8: Live Local Collection and Initial Data Commit

**Files:**
- Create at runtime: `data/raw/fred_WPU1017_<UTC_RUN_ID>.json`
- Create at runtime: `data/raw/ecos_base_rate_<UTC_RUN_ID>.json`
- Create at runtime: `data/processed/monthly_indicators.csv`

**Interfaces:**
- Consumes: the real local `.env` without printing it.
- Consumes: `python3 collect_data.py`.
- Produces: one verified local raw-data pair and merged CSV.
- Produces: initial public data commit containing generated data only.

- [ ] **Step 1: Run all tests before using real API keys**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 26 tests` and `OK`.

- [ ] **Step 2: Run one live collection**

Before running, explain to the user:

> 지금부터 `.env`의 두 키를 화면에 표시하지 않고 ECOS와 FRED에 읽기
> 요청을 보냅니다. 프로젝트 안에 원본 JSON 두 개와 CSV 하나가 생기며,
> 아직 GitHub로 전송되지는 않습니다.

Run:

```bash
python3 collect_data.py
```

Expected: exit code `0`, four Korean progress lines, and a final
`완료: data/processed/monthly_indicators.csv` line.

- [ ] **Step 3: Verify the generated file set and CSV shape**

Run:

```bash
find data/raw -maxdepth 1 -type f -name '*.json' -print
head -n 5 data/processed/monthly_indicators.csv
wc -l data/processed/monthly_indicators.csv
```

Expected:

- at least one `fred_WPU1017_*.json`;
- at least one `ecos_base_rate_*.json`;
- CSV header `month,korea_base_rate_percent,us_steel_ppi_index`;
- approximately 61 monthly data rows plus one header.

- [ ] **Step 4: Verify that no real key appears in code, docs, tests, or data**

Run:

```bash
set -a
source .env
set +a
if rg -F -l -- "$FRED_API_KEY" collector collect_data.py tests data README.md docs; then
  echo "FRED key exposure detected."
  exit 1
fi
if rg -F -l -- "$ECOS_API_KEY" collector collect_data.py tests data README.md docs; then
  echo "ECOS key exposure detected."
  exit 1
fi
echo "No API key values found in project outputs."
```

Expected: `No API key values found in project outputs.` and exit code `0`.
The commands must never print the key values.

- [ ] **Step 5: Verify `.env` is ignored and generated data is visible to Git**

Run:

```bash
git check-ignore -v .env
git ls-files .env
git status --short
```

Expected:

- `git check-ignore` identifies the `.env` rule;
- `git ls-files .env` prints nothing;
- `git status` lists generated JSON and CSV but never `.env`.

- [ ] **Step 6: Commit only the initial generated data**

Run:

```bash
git add -- data/raw data/processed/monthly_indicators.csv
git diff --cached --name-only
git commit -m "data: add initial economic indicators"
```

Expected: staged and committed paths are limited to `data/raw/*.json` and
`data/processed/monthly_indicators.csv`.

---

### Task 9: Fork, Push, Secrets, and First GitHub Run

**Files and external state:**
- Create on GitHub: public fork `suhyeonhong-bit/ToSuhyeon`.
- Modify local Git remotes: `origin` becomes the fork; `upstream` remains `yealu/ToSuhyeon`.
- Create on GitHub: Actions secrets `FRED_API_KEY`, `ECOS_API_KEY`.
- Create on GitHub: first manual workflow run and its data-only commit.

**Interfaces:**
- Consumes: all local commits from Tasks 1–8.
- Consumes: GitHub account `suhyeonhong-bit`.
- Produces: fork default branch `main` with code, workflow, and initial data.
- Produces: successful manual `Collect weekly economic data` workflow run.
- Produces: future Monday 11:00 Asia/Seoul scheduled runs.

- [ ] **Step 1: Create the public fork without changing the original**

Using the authenticated GitHub account `suhyeonhong-bit`:

1. Open `https://github.com/yealu/ToSuhyeon`.
2. Click `Fork`.
3. Set owner to `suhyeonhong-bit`.
4. Keep repository name `ToSuhyeon`.
5. Keep the public visibility inherited from the original.
6. Create the fork.
7. Confirm the resulting URL is
   `https://github.com/suhyeonhong-bit/ToSuhyeon`.

Expected: the fork exists and the original `yealu/ToSuhyeon` has no changes.

- [ ] **Step 2: Point local `origin` to the fork and retain the source as `upstream`**

Run:

```bash
git remote rename origin upstream
git remote add origin https://github.com/suhyeonhong-bit/ToSuhyeon.git
git remote -v
```

Expected:

```text
origin    https://github.com/suhyeonhong-bit/ToSuhyeon.git (fetch)
origin    https://github.com/suhyeonhong-bit/ToSuhyeon.git (push)
upstream  https://github.com/yealu/ToSuhyeon.git (fetch)
upstream  https://github.com/yealu/ToSuhyeon.git (push)
```

- [ ] **Step 3: Push the completed `main` branch to the fork**

Run:

```bash
git push -u origin main
```

Expected: local `main` tracks `origin/main`; the fork shows all code,
workflow, docs, tests, and the initial generated data.

- [ ] **Step 4: Have the user register the two Actions secrets directly**

Pause and tell the user:

> GitHub의 비밀 입력란은 사용자가 직접 작성해야 합니다. 키 값은 이
> 대화창에 보내지 마세요.

The user performs:

1. Open `https://github.com/suhyeonhong-bit/ToSuhyeon/settings/secrets/actions`.
2. Click `New repository secret`.
3. Enter name `FRED_API_KEY`.
4. Paste the real FRED key into the GitHub value field and save.
5. Click `New repository secret` again.
6. Enter name `ECOS_API_KEY`.
7. Paste the real ECOS key into the GitHub value field and save.
8. Confirm only that both secret names are listed; do not share their values.

Expected: the GitHub page lists `FRED_API_KEY` and `ECOS_API_KEY`.

- [ ] **Step 5: Trigger the first workflow manually**

Using GitHub:

1. Open the fork’s `Actions` tab.
2. If GitHub shows a disabled-workflow notice for the public fork, read the
   notice and click the button that enables the fork’s workflows.
3. Select `Collect weekly economic data`.
4. Click `Run workflow`.
5. Select branch `main`.
6. Click the green `Run workflow` button.
7. Open the new run and wait for completion.

Expected:

- `Run tests` succeeds;
- `Collect ECOS and FRED data` succeeds;
- `Commit generated data` succeeds;
- the run shows a green check;
- no log line contains either key value or a URL containing a key.

- [ ] **Step 6: Verify the automatic commit changed only generated data**

Run:

```bash
git fetch origin main
git log -1 --format='%h %s' origin/main
git diff-tree --no-commit-id --name-only -r origin/main
```

Expected:

- latest message starts with `data: collect weekly indicators`;
- every changed path begins with `data/raw/` or equals
  `data/processed/monthly_indicators.csv`.

- [ ] **Step 7: Fast-forward the local checkout and rerun verification**

Run:

```bash
git pull --ff-only origin main
python3 -m unittest discover -s tests -v
git status --short --branch
```

Expected:

- pull fast-forwards to the workflow-created data commit;
- `Ran 26 tests` and `OK`;
- status is clean and local `main` matches `origin/main`.

- [ ] **Step 8: Verify the final schedule and public outputs**

Run:

```bash
rg -n 'cron: "0 11 \\* \\* 1"|timezone: "Asia/Seoul"|workflow_dispatch|contents: write' .github/workflows/collect-weekly.yml
find data/raw -maxdepth 1 -type f -name '*.json' -print
head -n 5 data/processed/monthly_indicators.csv
```

Expected:

- the four workflow settings are present;
- raw FRED and ECOS JSON files from local and GitHub runs are present;
- the processed CSV is readable and has the expected three-column header.

---

## Final Verification Checklist

- [ ] `python3 -m unittest discover -s tests -v` reports 26 tests and `OK`.
- [ ] `python3 -m compileall -q collect_data.py collector tests` exits `0`.
- [ ] Local live collection creates raw FRED JSON, raw ECOS JSON, and merged CSV.
- [ ] Secret-value scan finds no key in tracked or generated project files.
- [ ] `.env` remains ignored and untracked.
- [ ] The fork is `suhyeonhong-bit/ToSuhyeon`; original `yealu/ToSuhyeon` is unchanged.
- [ ] GitHub Actions uses Monday 11:00 `Asia/Seoul`, manual dispatch, and only `contents: write`.
- [ ] The first manual workflow run succeeds on GitHub-hosted infrastructure.
- [ ] The workflow-created commit changes generated data only.
- [ ] Local `main` is clean and matches `origin/main` after the final pull.
