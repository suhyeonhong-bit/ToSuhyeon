import csv
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, Mapping, Optional, Sequence, TextIO

from collector.errors import CollectorError


CSV_FIELDS = (
    "month",
    "korea_base_rate_percent",
    "us_steel_ppi_index",
)
RAW_PREFIXES = {
    "fred": "fred_WPU1017",
    "ecos": "ecos_base_rate",
}


def _atomic_text_write(
    target: Path,
    write_content: Callable[[TextIO], None],
    encoding: str,
    newline: Optional[str] = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline=newline,
            dir=str(target.parent),
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            write_content(temporary_file)
        os.replace(str(temporary_path), str(target))
    except (OSError, UnicodeError, ValueError, csv.Error):
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise CollectorError(
            f"수집 실패: {target.name} 파일을 안전하게 저장하지 못했습니다."
        ) from None


def save_raw_response(
    raw_dir: Path,
    source: str,
    raw_text: str,
    secrets: Sequence[str],
    run_id: str,
) -> Path:
    prefix = RAW_PREFIXES.get(source)
    if prefix is None:
        raise CollectorError(
            "수집 실패: 알 수 없는 원본 데이터 출처입니다."
        )
    if any(secret and secret in raw_text for secret in secrets):
        raise CollectorError(
            "수집 실패: 원본 응답에 비밀 키가 포함되어 저장을 중단했습니다."
        )
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        raise CollectorError(
            "수집 실패: 올바른 JSON만 원본으로 저장할 수 있습니다."
        ) from None
    if not isinstance(parsed, dict):
        raise CollectorError(
            "수집 실패: JSON 원본의 최상위 구조가 객체가 아닙니다."
        )

    target = raw_dir / f"{prefix}_{run_id}.json"
    _atomic_text_write(
        target,
        lambda handle: handle.write(raw_text),
        encoding="utf-8",
    )
    return target


def save_csv(
    output_path: Path,
    rows: Sequence[Mapping[str, str]],
) -> Path:
    if not rows:
        raise CollectorError(
            "수집 실패: 저장할 월별 CSV 행이 없습니다."
        )

    def write_rows(handle: TextIO) -> None:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)

    _atomic_text_write(
        output_path,
        write_rows,
        encoding="utf-8-sig",
        newline="",
    )
    return output_path
