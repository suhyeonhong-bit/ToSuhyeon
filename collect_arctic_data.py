import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional
from zoneinfo import ZoneInfo

from arctic_collector.config import load_arctic_config
from arctic_collector.eia import fetch_eia_steo
from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import (
    SourceResult,
    merge_collection_results,
)
from arctic_collector.sanctions import fetch_eu, fetch_ofac
from arctic_collector.sea_ice import fetch_nsidc
from arctic_collector.storage import load_dashboard, save_dashboard


GROUP_SOURCES = {
    "eia": ("eia",),
    "daily": ("ofac", "eu", "nsidc"),
    "all": ("eia", "ofac", "eu", "nsidc"),
}


def _safe_failure(source: str, error: ArcticCollectorError) -> str:
    status = f" HTTP {error.status}" if error.status is not None else ""
    return f"{source}: {error.kind}{status}"


def run(
    project_root: Path,
    group: str,
    now: Optional[datetime] = None,
    fetchers: Optional[Mapping[str, Callable[[], SourceResult]]] = None,
) -> int:
    if group not in GROUP_SOURCES:
        raise ValueError("unknown collection group")
    moment = datetime.now(timezone.utc) if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    require_eia = "eia" in GROUP_SOURCES[group]
    try:
        config = load_arctic_config(project_root / ".env", require_eia=require_eia)
        output_path = project_root / "data" / "processed" / "arctic_dashboard.json"
        previous = load_dashboard(output_path)
    except ArcticCollectorError as error:
        print(_safe_failure(error.source, error), file=sys.stderr)
        return 1

    source_fetchers: Dict[str, Callable[[], SourceResult]]
    if fetchers is None:
        collection_date = moment.astimezone(ZoneInfo("Asia/Seoul")).date()
        source_fetchers = {
            "eia": lambda: fetch_eia_steo(config.eia_api_key or "", collection_date),
            "ofac": fetch_ofac,
            "eu": fetch_eu,
            "nsidc": fetch_nsidc,
        }
    else:
        source_fetchers = dict(fetchers)

    successes: Dict[str, SourceResult] = {}
    failures: Dict[str, ArcticCollectorError] = {}
    for source in GROUP_SOURCES[group]:
        try:
            result = source_fetchers[source]()
            successes[source] = result
            print(f"{source}: fresh · data through {result.data_through}")
        except ArcticCollectorError as error:
            failures[source] = error
            print(_safe_failure(source, error), file=sys.stderr)
        except Exception:
            error = ArcticCollectorError(
                source,
                "internal",
                "예상하지 못한 수집 오류가 발생했습니다.",
            )
            failures[source] = error
            print(_safe_failure(source, error), file=sys.stderr)

    if not successes:
        print("manifest: all-failed", file=sys.stderr)
        return 1

    try:
        document = merge_collection_results(
            previous,
            GROUP_SOURCES[group],
            successes,
            failures,
            moment,
        )
        save_dashboard(
            output_path,
            document,
            secrets=(config.eia_api_key or "",),
        )
    except ArcticCollectorError as error:
        print(_safe_failure(error.source, error), file=sys.stderr)
        return 1
    print(f"saved: {output_path.relative_to(project_root)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect official Arctic dashboard data")
    parser.add_argument("--group", choices=tuple(GROUP_SOURCES), required=True)
    arguments = parser.parse_args()
    return run(Path(__file__).resolve().parent, arguments.group)


if __name__ == "__main__":
    raise SystemExit(main())
