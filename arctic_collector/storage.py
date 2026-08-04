import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Mapping, Optional, Sequence

from arctic_collector.errors import ArcticCollectorError
from arctic_collector.manifest import validate_dashboard


def load_dashboard(path: Path) -> Optional[Dict[str, object]]:
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ArcticCollectorError(
            "storage", "format", "기존 북극 대시보드 JSON을 읽지 못했습니다."
        ) from None
    if not isinstance(document, dict):
        raise ArcticCollectorError(
            "storage", "format", "기존 북극 대시보드 JSON이 객체가 아닙니다."
        )
    validate_dashboard(document)
    return document


def save_dashboard(
    path: Path,
    document: Mapping[str, object],
    secrets: Sequence[str],
) -> Path:
    validate_dashboard(document)
    serialized = json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    if any(secret and secret in serialized for secret in secrets):
        raise ArcticCollectorError(
            "storage", "secret", "생성 JSON에서 비밀값을 발견해 저장을 중단했습니다."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(str(temporary_path), str(path))
    except (OSError, UnicodeError, ValueError):
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise ArcticCollectorError(
            "storage", "write", "북극 대시보드 JSON을 안전하게 저장하지 못했습니다."
        ) from None
    return path
