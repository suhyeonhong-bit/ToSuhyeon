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
