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
