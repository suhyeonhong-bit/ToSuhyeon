from decimal import Decimal, InvalidOperation
from typing import Dict, List, Mapping, Optional

from collector.errors import CollectorError


def calculate_target_rate(
    upper_values: Mapping[str, Optional[str]],
    lower_values: Mapping[str, Optional[str]],
) -> Dict[str, Optional[str]]:
    """Calculate monthly midpoints for the shared target-rate bounds."""
    months = sorted(set(upper_values) & set(lower_values))
    if not months:
        raise CollectorError(
            "수집 실패: 연준 목표금리의 공통 월별 데이터가 없습니다."
        )

    values: Dict[str, Optional[str]] = {}
    usable = False
    for month in months:
        upper = upper_values.get(month)
        lower = lower_values.get(month)
        if upper is None or lower is None:
            values[month] = None
            continue
        try:
            midpoint = (Decimal(upper) + Decimal(lower)) / Decimal("2")
        except (InvalidOperation, TypeError, ValueError):
            raise CollectorError(
                f"수집 실패: 연준 목표금리 {month} 값이 숫자가 아닙니다."
            ) from None
        if not midpoint.is_finite():
            raise CollectorError(
                f"수집 실패: 연준 목표금리 {month} 값이 숫자가 아닙니다."
            )
        values[month] = format(midpoint, "f")
        usable = True

    if not usable:
        raise CollectorError(
            "수집 실패: 연준 목표금리에서 사용할 수 있는 월별 값을 받지 못했습니다."
        )
    return values


def merge_monthly(
    ecos_values: Mapping[str, Optional[str]],
    fred_values: Mapping[str, Optional[str]],
    fed_target_values: Optional[Mapping[str, Optional[str]]] = None,
) -> List[Dict[str, str]]:
    if fed_target_values is None:
        fed_target_values = {}
    months = sorted(
        set(ecos_values) | set(fred_values) | set(fed_target_values)
    )
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
                "us_fed_target_rate_percent": fed_target_values.get(month) or "",
            }
        )
    return rows
