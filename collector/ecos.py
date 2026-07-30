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
