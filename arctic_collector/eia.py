import hashlib
import json
import math
from datetime import date
from typing import Callable, Dict, List, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import SourceResult


EIA_API_URL = "https://api.eia.gov/v2/steo/data/"
EIA_PUBLIC_URL = "https://www.eia.gov/outlooks/steo/"
SERIES = {
    "NGEXPUS_LNG": "usLngExports",
    "NGPRPUS": "usDryGasProduction",
    "NGHHUUS": "henryHub",
}


def _format_error() -> ArcticCollectorError:
    return ArcticCollectorError("eia", "format", "EIA 응답 형식이 올바르지 않습니다.")


def parse_eia_steo(
    payload: Mapping[str, object],
    as_of: date,
) -> Dict[str, List[Dict[str, object]]]:
    try:
        response = payload["response"]
        if not isinstance(response, dict):
            raise TypeError
        rows = response["data"]
        if not isinstance(rows, list):
            raise TypeError
    except (KeyError, TypeError):
        raise _format_error() from None

    output: Dict[str, List[Dict[str, object]]] = {
        name: [] for name in SERIES.values()
    }
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise _format_error()
        try:
            series_id = str(row["seriesId"])
            period = str(row["period"])
            unit = str(row["unit"])
            value = float(row["value"])
            year = int(period)
        except (KeyError, TypeError, ValueError):
            raise _format_error() from None
        if series_id not in SERIES or not (period.isdigit() and len(period) == 4):
            raise _format_error()
        if not math.isfinite(value) or not unit:
            raise _format_error()
        key = (series_id, period)
        if key in seen:
            raise _format_error()
        seen.add(key)
        output[SERIES[series_id]].append(
            {
                "period": period,
                "value": value,
                "unit": unit,
                "kind": "forecast" if year >= as_of.year else "actual",
                "source": "EIA STEO",
            }
        )

    for points in output.values():
        points.sort(key=lambda point: str(point["period"]))
        if not points:
            raise _format_error()
    return output


def fetch_eia_steo(
    api_key: str,
    as_of: date,
    opener: Callable[..., object] = urlopen,
) -> SourceResult:
    query_items = [
        ("api_key", api_key),
        ("frequency", "annual"),
        ("data[0]", "value"),
        ("facets[seriesId][]", "NGEXPUS_LNG"),
        ("facets[seriesId][]", "NGPRPUS"),
        ("facets[seriesId][]", "NGHHUUS"),
        ("start", "2016"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("length", "500"),
    ]
    request = Request(
        f"{EIA_API_URL}?{urlencode(query_items)}",
        headers={"User-Agent": "ToSuhyeon-Arctic-Collector/1.0"},
    )
    try:
        with opener(request, timeout=30) as response:
            raw = response.read()
    except Exception as error:
        status = getattr(error, "code", None)
        raise ArcticCollectorError(
            "eia",
            "http" if status is not None else "network",
            "EIA 데이터를 가져오지 못했습니다.",
            status=status,
        ) from None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _format_error() from None
    data = parse_eia_steo(payload, as_of)
    data_through = max(
        str(point["period"])
        for points in data.values()
        for point in points
    )
    return SourceResult(
        data=data,
        content_hash=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        data_through=data_through,
        public_url=EIA_PUBLIC_URL,
        edition=as_of.strftime("%Y-%m"),
    )
