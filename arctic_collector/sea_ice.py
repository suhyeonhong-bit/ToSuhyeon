import csv
import hashlib
import io
import math
from datetime import date
from typing import Callable, Dict
from urllib.request import Request, urlopen

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import SourceResult


NSIDC_URL = "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv"


def _format_error() -> ArcticCollectorError:
    return ArcticCollectorError("nsidc", "format", "NSIDC CSV 형식이 올바르지 않습니다.")


def parse_nsidc_csv(text: str, retain_days: int = 400) -> Dict[str, object]:
    if retain_days < 1:
        raise _format_error()
    try:
        reader = csv.reader(io.StringIO(text.lstrip("\ufeff")))
        header = next(reader)
        units = next(reader)
    except (StopIteration, csv.Error):
        raise _format_error() from None
    if [cell.strip() for cell in header[:5]] != ["Year", "Month", "Day", "Extent", "Missing"]:
        raise _format_error()
    if len(units) < 5 or units[3].strip() != "10^6 sq km":
        raise _format_error()

    observations = []
    seen = set()
    try:
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) < 5:
                raise _format_error()
            observed = date(int(row[0]), int(row[1]), int(row[2])).isoformat()
            extent = float(row[3])
            missing = float(row[4])
            if not math.isfinite(extent) or not math.isfinite(missing) or observed in seen:
                raise _format_error()
            seen.add(observed)
            observations.append(
                {
                    "date": observed,
                    "extent": extent,
                    "unit": "10^6 sq km",
                    "missing": missing,
                    "source": "NSIDC Sea Ice Index v4",
                }
            )
    except (ValueError, csv.Error):
        raise _format_error() from None
    if not observations:
        raise _format_error()
    observations.sort(key=lambda row: str(row["date"]))
    observations = observations[-retain_days:]
    return {"latest": dict(observations[-1]), "daily": observations}


def fetch_nsidc(opener: Callable[..., object] = urlopen) -> SourceResult:
    request = Request(NSIDC_URL, headers={"User-Agent": "ToSuhyeon-Arctic-Collector/1.0"})
    try:
        with opener(request, timeout=45) as response:
            raw = response.read()
    except Exception as error:
        status = getattr(error, "code", None)
        raise ArcticCollectorError(
            "nsidc",
            "http" if status is not None else "network",
            "NSIDC 데이터를 가져오지 못했습니다.",
            status=status,
        ) from None
    try:
        data = parse_nsidc_csv(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise _format_error() from None
    return SourceResult(
        data=data,
        content_hash=f"sha256:{hashlib.sha256(raw).hexdigest()}",
        data_through=str(data["latest"]["date"]),
        public_url=NSIDC_URL,
    )
