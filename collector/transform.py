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
