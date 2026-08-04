import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

from arctic_collector.errors import ArcticCollectorError


@dataclass(frozen=True)
class ArcticConfig:
    eia_api_key: Optional[str]


def _read_env_file(env_path: Path) -> Dict[str, str]:
    if not env_path.is_file():
        return {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise ArcticCollectorError(
            "config",
            "file",
            ".env 파일을 읽지 못했습니다.",
        ) from None

    values: Dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "=" not in raw_line:
            raise ArcticCollectorError(
                "config",
                "format",
                f".env {line_number}번째 줄 형식이 올바르지 않습니다.",
            )
        name, value = raw_line.split("=", 1)
        if name.strip():
            values[name.strip()] = value
    return values


def load_arctic_config(
    env_path: Path,
    require_eia: bool,
    environ: Optional[Mapping[str, str]] = None,
) -> ArcticConfig:
    environment = os.environ if environ is None else environ
    file_values = _read_env_file(env_path)
    value = environment.get("EIA_API_KEY", file_values.get("EIA_API_KEY", ""))
    if not value:
        if require_eia:
            raise ArcticCollectorError(
                "config",
                "missing-secret",
                "EIA_API_KEY가 없습니다.",
            )
        return ArcticConfig(eia_api_key=None)
    if any(character.isspace() for character in value):
        raise ArcticCollectorError(
            "config",
            "invalid-secret",
            "EIA_API_KEY에 공백이 포함되어 있습니다.",
        )
    return ArcticConfig(eia_api_key=value)
