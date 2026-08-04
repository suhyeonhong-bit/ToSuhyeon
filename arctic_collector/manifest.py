import copy
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Mapping, Optional, Sequence

from arctic_collector.errors import ArcticCollectorError


@dataclass(frozen=True)
class SourceResult:
    data: Mapping[str, object]
    content_hash: str
    data_through: str
    public_url: str
    edition: Optional[str] = None


SOURCE_NAMES = ("eia", "ofac", "eu", "nsidc")
SOURCE_URLS = {
    "eia": "https://www.eia.gov/outlooks/steo/",
    "ofac": "https://ofac.treasury.gov/sanctions-list-service",
    "eu": (
        "https://data.europa.eu/data/datasets/"
        "consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions"
        "?locale=en"
    ),
    "nsidc": "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv",
}
WATCHLIST = (
    ("novatek", "NOVATEK"),
    ("yamal-lng", "Yamal LNG"),
    ("leonid-mikhelson", "Leonid Mikhelson"),
    ("gennady-timchenko", "Gennady Timchenko"),
)


def _empty_source(name: str) -> Dict[str, object]:
    metadata: Dict[str, object] = {
        "status": "stale",
        "hasData": False,
        "lastAttemptAt": None,
        "lastSuccessAt": None,
        "dataThrough": None,
        "url": SOURCE_URLS[name],
        "contentHash": None,
    }
    if name == "eia":
        metadata["edition"] = None
    return metadata


def empty_dashboard() -> Dict[str, object]:
    return {
        "schemaVersion": 1,
        "generatedAt": "1970-01-01T00:00:00Z",
        "sources": {name: _empty_source(name) for name in SOURCE_NAMES},
        "energy": {
            "usLngExports": [],
            "usDryGasProduction": [],
            "henryHub": [],
        },
        "sanctions": {
            "watchlist": [
                {
                    "id": watch_id,
                    "label": label,
                    "ofac": {"listed": False, "matches": []},
                    "eu": {"listed": False, "matches": []},
                }
                for watch_id, label in WATCHLIST
            ]
        },
        "seaIce": {"latest": None, "daily": []},
    }


def _schema_error() -> ArcticCollectorError:
    return ArcticCollectorError(
        "manifest",
        "format",
        "북극 대시보드 JSON 스키마가 올바르지 않습니다.",
    )


def _is_iso_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _validate_source(name: str, source: object) -> None:
    if not isinstance(source, dict):
        raise _schema_error()
    required = {
        "status",
        "hasData",
        "lastAttemptAt",
        "lastSuccessAt",
        "dataThrough",
        "url",
        "contentHash",
    }
    allowed = required | ({"edition"} if name == "eia" else set())
    if set(source) != allowed:
        raise _schema_error()
    if source["status"] not in {"fresh", "stale"} or not isinstance(source["hasData"], bool):
        raise _schema_error()
    if not isinstance(source["url"], str) or not source["url"].startswith("https://"):
        raise _schema_error()
    for field in ("lastAttemptAt", "lastSuccessAt"):
        if source[field] is not None and not _is_iso_timestamp(source[field]):
            raise _schema_error()
    if source["hasData"]:
        if source["lastSuccessAt"] is None or not isinstance(source["dataThrough"], str):
            raise _schema_error()
        if not isinstance(source["contentHash"], str) or re.fullmatch(
            r"sha256:[0-9a-f]{64}", source["contentHash"]
        ) is None:
            raise _schema_error()
    elif source["contentHash"] is not None:
        raise _schema_error()
    if name == "eia" and source["edition"] is not None:
        if not isinstance(source["edition"], str) or re.fullmatch(r"\d{4}-\d{2}", source["edition"]) is None:
            raise _schema_error()


def _validate_energy(energy: object) -> None:
    if not isinstance(energy, dict) or set(energy) != {
        "usLngExports", "usDryGasProduction", "henryHub"
    }:
        raise _schema_error()
    for points in energy.values():
        if not isinstance(points, list):
            raise _schema_error()
        periods = []
        unit = None
        for point in points:
            if not isinstance(point, dict) or set(point) != {
                "period", "value", "unit", "kind", "source"
            }:
                raise _schema_error()
            if not isinstance(point["period"], str) or re.fullmatch(r"\d{4}", point["period"]) is None:
                raise _schema_error()
            if isinstance(point["value"], bool) or not isinstance(point["value"], (int, float)) or not math.isfinite(point["value"]):
                raise _schema_error()
            if point["kind"] not in {"actual", "forecast"} or point["source"] != "EIA STEO":
                raise _schema_error()
            if not isinstance(point["unit"], str) or not point["unit"]:
                raise _schema_error()
            if unit is None:
                unit = point["unit"]
            elif point["unit"] != unit:
                raise _schema_error()
            periods.append(point["period"])
        if periods != sorted(set(periods)):
            raise _schema_error()


def _validate_match(match: object) -> None:
    if not isinstance(match, dict) or set(match) != {
        "officialName", "list", "programs", "officialId"
    }:
        raise _schema_error()
    if not all(isinstance(match[field], str) and match[field] for field in ("officialName", "list", "officialId")):
        raise _schema_error()
    if not isinstance(match["programs"], list) or not all(
        isinstance(program, str) and program for program in match["programs"]
    ):
        raise _schema_error()


def _validate_sanctions(sanctions: object) -> None:
    if not isinstance(sanctions, dict) or set(sanctions) != {"watchlist"}:
        raise _schema_error()
    watchlist = sanctions["watchlist"]
    if not isinstance(watchlist, list) or len(watchlist) != len(WATCHLIST):
        raise _schema_error()
    for item, (expected_id, expected_label) in zip(watchlist, WATCHLIST):
        if not isinstance(item, dict) or set(item) != {"id", "label", "ofac", "eu"}:
            raise _schema_error()
        if item["id"] != expected_id or item["label"] != expected_label:
            raise _schema_error()
        for source_name in ("ofac", "eu"):
            source = item[source_name]
            if not isinstance(source, dict) or set(source) != {"listed", "matches"}:
                raise _schema_error()
            if not isinstance(source["listed"], bool) or not isinstance(source["matches"], list):
                raise _schema_error()
            if source["listed"] != bool(source["matches"]):
                raise _schema_error()
            for match in source["matches"]:
                _validate_match(match)


def _validate_sea_point(point: object) -> None:
    if not isinstance(point, dict) or set(point) != {
        "date", "extent", "unit", "missing", "source"
    }:
        raise _schema_error()
    try:
        datetime.strptime(point["date"], "%Y-%m-%d")
    except (TypeError, ValueError):
        raise _schema_error() from None
    if point["unit"] != "10^6 sq km" or point["source"] != "NSIDC Sea Ice Index v4":
        raise _schema_error()
    for field in ("extent", "missing"):
        if isinstance(point[field], bool) or not isinstance(point[field], (int, float)) or not math.isfinite(point[field]):
            raise _schema_error()


def _validate_sea_ice(sea_ice: object) -> None:
    if not isinstance(sea_ice, dict) or set(sea_ice) != {"latest", "daily"}:
        raise _schema_error()
    daily = sea_ice["daily"]
    if not isinstance(daily, list):
        raise _schema_error()
    dates = []
    for point in daily:
        _validate_sea_point(point)
        dates.append(point["date"])
    if dates != sorted(set(dates)):
        raise _schema_error()
    if not daily:
        if sea_ice["latest"] is not None:
            raise _schema_error()
    elif sea_ice["latest"] != daily[-1]:
        raise _schema_error()


def validate_dashboard(document: Mapping[str, object]) -> None:
    if not isinstance(document, dict) or set(document) != {
        "schemaVersion", "generatedAt", "sources", "energy", "sanctions", "seaIce"
    }:
        raise _schema_error()
    if document["schemaVersion"] != 1 or not _is_iso_timestamp(document["generatedAt"]):
        raise _schema_error()
    sources = document["sources"]
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_NAMES):
        raise _schema_error()
    for name in SOURCE_NAMES:
        _validate_source(name, sources[name])
    _validate_energy(document["energy"])
    _validate_sanctions(document["sanctions"])
    _validate_sea_ice(document["seaIce"])


def _timestamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def merge_collection_results(
    previous: Optional[Mapping[str, object]],
    requested_sources: Sequence[str],
    successes: Mapping[str, SourceResult],
    failures: Mapping[str, ArcticCollectorError],
    attempted_at: datetime,
) -> Dict[str, object]:
    if not successes:
        raise ArcticCollectorError(
            "manifest", "all-failed", "요청한 모든 북극 데이터 수집이 실패했습니다."
        )
    if not set(requested_sources).issubset(SOURCE_NAMES):
        raise _schema_error()
    document = copy.deepcopy(previous) if previous is not None else empty_dashboard()
    validate_dashboard(document)
    attempted = _timestamp(attempted_at)

    for name in requested_sources:
        if name in successes:
            result = successes[name]
            metadata = {
                "status": "fresh",
                "hasData": True,
                "lastAttemptAt": attempted,
                "lastSuccessAt": attempted,
                "dataThrough": result.data_through,
                "url": result.public_url,
                "contentHash": result.content_hash,
            }
            if name == "eia":
                metadata["edition"] = result.edition
                document["energy"] = copy.deepcopy(result.data)
            elif name == "nsidc":
                document["seaIce"] = copy.deepcopy(result.data)
            else:
                for item in document["sanctions"]["watchlist"]:
                    matches = copy.deepcopy(result.data[item["id"]])
                    item[name] = {"listed": bool(matches), "matches": matches}
            document["sources"][name] = metadata
        elif name in failures:
            document["sources"][name]["status"] = "stale"
            document["sources"][name]["lastAttemptAt"] = attempted
        else:
            raise _schema_error()

    document["generatedAt"] = attempted
    validate_dashboard(document)
    return document
