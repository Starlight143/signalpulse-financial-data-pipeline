"""Ingestion exceptions."""

from typing import Any


class IngestionError(Exception):
    def __init__(self, message: str, exchange: str | None = None, symbol: str | None = None):
        self.exchange = exchange
        self.symbol = symbol
        super().__init__(message)


class IngestionRateLimitError(IngestionError):
    def __init__(self, retry_after: int, exchange: str | None = None):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited by {exchange}. Retry after {retry_after}s",
            exchange=exchange,
        )


class IngestionConnectionError(IngestionError):
    pass


class IngestionDataError(IngestionError):
    def __init__(
        self,
        message: str,
        raw_data: dict[str, Any] | None = None,
        exchange: str | None = None,
    ):
        self.raw_data = raw_data
        super().__init__(message, exchange=exchange)
