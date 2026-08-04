from typing import Optional


class ArcticCollectorError(Exception):
    """A source-scoped error whose message is safe to print."""

    def __init__(
        self,
        source: str,
        kind: str,
        message: str,
        status: Optional[int] = None,
    ) -> None:
        self.source = source
        self.kind = kind
        self.status = status
        safe_status = f" (HTTP {status})" if status is not None else ""
        super().__init__(f"{source}: {message}{safe_status}")
