import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Callable, Dict, List, Mapping, Tuple
from urllib.request import Request, urlopen

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import SourceResult


OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_NON_SDN_URL = "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv"
OFAC_PUBLIC_URL = "https://ofac.treasury.gov/sanctions-list-service"
EU_METADATA_URL = (
    "https://data.europa.eu/api/hub/repo/datasets/"
    "consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions/"
    "distributions?valueType=metadata&limit=100"
)
EU_PUBLIC_URL = (
    "https://data.europa.eu/data/datasets/"
    "consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions"
    "?locale=en"
)
WATCHLIST = {
    "novatek": {
        "label": "NOVATEK",
        "aliases": {
            "NOVATEK",
            "PAO NOVATEK",
            "NOVATEK PAO",
            "PUBLIC JOINT STOCK COMPANY NOVATEK",
        },
    },
    "yamal-lng": {
        "label": "Yamal LNG",
        "aliases": {"YAMAL LNG", "OAO YAMAL LNG", "YAMAL LNG JSC"},
    },
    "leonid-mikhelson": {
        "label": "Leonid Mikhelson",
        "aliases": {
            "LEONID MIKHELSON",
            "MIKHELSON LEONID",
            "LEONID VIKTOROVICH MIKHELSON",
            "MIKHELSON LEONID VIKTOROVICH",
        },
    },
    "gennady-timchenko": {
        "label": "Gennady Timchenko",
        "aliases": {
            "GENNADY TIMCHENKO",
            "TIMCHENKO GENNADY",
            "GENNADY NIKOLAYEVICH TIMCHENKO",
            "TIMCHENKO GENNADY NIKOLAYEVICH",
        },
    },
}


def _format_error(source: str) -> ArcticCollectorError:
    return ArcticCollectorError(source, "format", f"{source.upper()} 목록 형식이 올바르지 않습니다.")


def normalize_name(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", ascii_text.upper()).strip()


def _empty_matches() -> Dict[str, List[Dict[str, object]]]:
    return {watch_id: [] for watch_id in WATCHLIST}


def _matching_watch_id(name: str):
    normalized = normalize_name(name)
    for watch_id, item in WATCHLIST.items():
        if normalized in item["aliases"]:
            return watch_id
    return None


def _programs(value: str) -> List[str]:
    if value.strip() == "-0-":
        return []
    return sorted(set(re.findall(r"[A-Z][A-Z0-9-]+", value.upper())))


def parse_ofac_csv(
    text: str,
    list_name: str,
) -> Dict[str, List[Dict[str, object]]]:
    output = _empty_matches()
    try:
        rows = csv.reader(io.StringIO(text))
        for row in rows:
            if not row:
                continue
            if len(row) < 4:
                raise _format_error("ofac")
            official_id, official_name, _entity_type, program = row[:4]
            watch_id = _matching_watch_id(official_name)
            if watch_id is None:
                continue
            output[watch_id].append(
                {
                    "officialName": official_name,
                    "list": list_name,
                    "programs": _programs(program),
                    "officialId": official_id,
                }
            )
    except csv.Error:
        raise _format_error("ofac") from None
    return output


def _language_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("@value", ""))
    if isinstance(value, list):
        english = [item for item in value if isinstance(item, dict) and item.get("@language") == "en"]
        chosen = english[0] if english else (value[0] if value else "")
        return _language_text(chosen)
    return ""


def _id_value(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("@id", ""))
    if isinstance(value, list) and value:
        return _id_value(value[0])
    return ""


def resolve_eu_csv_url(payload: Mapping[str, object]) -> str:
    graph = payload.get("@graph")
    if not isinstance(graph, list):
        raise _format_error("eu")
    for distribution in graph:
        if not isinstance(distribution, dict):
            continue
        file_type = _id_value(distribution.get("dct:format"))
        title = _language_text(distribution.get("dct:title"))
        if file_type.rstrip("/").endswith("CSV") and "Consolidated Financial Sanctions File 1.1" in title:
            url = _id_value(distribution.get("dcat:downloadURL"))
            if url.startswith("https://"):
                return url
    raise _format_error("eu")


def parse_eu_csv(
    text: str,
) -> Tuple[Dict[str, List[Dict[str, object]]], str]:
    output = _empty_matches()
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
        required = {
            "fileGenerationDate",
            "Entity_LogicalId",
            "Entity_EU_ReferenceNumber",
            "Entity_Regulation_Programme",
            "NameAlias_LastName",
            "NameAlias_FirstName",
            "NameAlias_MiddleName",
            "NameAlias_WholeName",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise _format_error("eu")
        data_dates = set()
        seen = set()
        for row in reader:
            data_dates.add(row["fileGenerationDate"])
            official_name = row["NameAlias_WholeName"].strip()
            if not official_name:
                official_name = " ".join(
                    part.strip()
                    for part in (
                        row["NameAlias_FirstName"],
                        row["NameAlias_MiddleName"],
                        row["NameAlias_LastName"],
                    )
                    if part.strip()
                )
            watch_id = _matching_watch_id(official_name)
            if watch_id is None:
                continue
            identity = (watch_id, row["Entity_LogicalId"], official_name)
            if identity in seen:
                continue
            seen.add(identity)
            programs = sorted(
                set(filter(None, re.split(r"[,;|]", row["Entity_Regulation_Programme"])))
            )
            output[watch_id].append(
                {
                    "officialName": official_name,
                    "list": "EU Consolidated Financial Sanctions List",
                    "programs": programs,
                    "officialId": row["Entity_EU_ReferenceNumber"],
                }
            )
        if len(data_dates) != 1:
            raise _format_error("eu")
        data_through = datetime.strptime(data_dates.pop(), "%d/%m/%Y").date().isoformat()
    except (csv.Error, KeyError, TypeError, ValueError):
        raise _format_error("eu") from None
    return output, data_through


def _download(url: str, source: str, opener: Callable[..., object]) -> bytes:
    request = Request(url, headers={"User-Agent": "ToSuhyeon-Arctic-Collector/1.0"})
    try:
        with opener(request, timeout=45) as response:
            return response.read()
    except Exception as error:
        status = getattr(error, "code", None)
        raise ArcticCollectorError(
            source,
            "http" if status is not None else "network",
            f"{source.upper()} 데이터를 가져오지 못했습니다.",
            status=status,
        ) from None


def fetch_ofac(opener: Callable[..., object] = urlopen) -> SourceResult:
    sdn_raw = _download(OFAC_SDN_URL, "ofac", opener)
    non_sdn_raw = _download(OFAC_NON_SDN_URL, "ofac", opener)
    try:
        sdn = parse_ofac_csv(sdn_raw.decode("utf-8-sig"), "SDN")
        non_sdn = parse_ofac_csv(non_sdn_raw.decode("utf-8-sig"), "Non-SDN")
    except UnicodeDecodeError:
        raise _format_error("ofac") from None
    combined = _empty_matches()
    for watch_id in WATCHLIST:
        combined[watch_id] = sdn[watch_id] + non_sdn[watch_id]
    return SourceResult(
        data=combined,
        content_hash=f"sha256:{hashlib.sha256(sdn_raw + bytes([0]) + non_sdn_raw).hexdigest()}",
        data_through=datetime.now(timezone.utc).date().isoformat(),
        public_url=OFAC_PUBLIC_URL,
    )


def fetch_eu(opener: Callable[..., object] = urlopen) -> SourceResult:
    metadata_raw = _download(EU_METADATA_URL, "eu", opener)
    try:
        metadata = json.loads(metadata_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _format_error("eu") from None
    download_url = resolve_eu_csv_url(metadata)
    csv_raw = _download(download_url, "eu", opener)
    try:
        data, data_through = parse_eu_csv(csv_raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise _format_error("eu") from None
    return SourceResult(
        data=data,
        content_hash=f"sha256:{hashlib.sha256(csv_raw).hexdigest()}",
        data_through=data_through,
        public_url=EU_PUBLIC_URL,
    )
