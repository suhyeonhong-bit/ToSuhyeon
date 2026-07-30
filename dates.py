from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CollectionRange:
    start_month: str
    end_month: str
    start_date: str
    end_date: str


def calculate_collection_range(today: date) -> CollectionRange:
    start_year = today.year - 5
    return CollectionRange(
        start_month=f"{start_year:04d}{today.month:02d}",
        end_month=f"{today.year:04d}{today.month:02d}",
        start_date=f"{start_year:04d}-{today.month:02d}-01",
        end_date=today.isoformat(),
    )
