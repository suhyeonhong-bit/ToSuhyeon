import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

from collector.errors import CollectorError


@dataclass(frozen=True)
class Config:
    fred_api_key: str
    ecos_api_key: str


def _read_env_file(env_path: Path) -> Dict[str, str]:
    if not env_path.is_file():
        return {}

    values: Dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise CollectorError(
            "수집 실패: .env 파일을 읽지 못했습니다. 파일 위치와 권한을 확인해주세요."
        ) from None

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "=" not in raw_line:
            raise CollectorError(
                f"수집 실패: .env 파일 {line_number}번째 줄에 '='이 없습니다."
            )
        raw_name, raw_value = raw_line.split("=", 1)
        name = raw_name.strip()
        if name:
            values[name] = raw_value
    return values


def _required_key(
    name: str,
    file_values: Mapping[str, str],
    environment: Mapping[str, str],
) -> str:
    value = environment.get(name, file_values.get(name, ""))
    if not value:
        raise CollectorError(
            f"수집 실패: {name}이 없습니다. .env 또는 GitHub Actions secrets를 확인해주세요."
        )
    if any(character.isspace() for character in value):
        raise CollectorError(
            f"수집 실패: {name}에 공백이 포함되어 있습니다. 키를 다시 붙여넣어 주세요."
        )
    return value


def load_config(
    env_path: Path,
    environ: Optional[Mapping[str, str]] = None,
) -> Config:
    environment = os.environ if environ is None else environ
    file_values = _read_env_file(env_path)
    return Config(
        fred_api_key=_required_key(
            "FRED_API_KEY",
            file_values,
            environment,
        ),
        ecos_api_key=_required_key(
            "ECOS_API_KEY",
            file_values,
            environment,
        ),
    )
