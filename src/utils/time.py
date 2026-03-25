"""Time utilities."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_timestamp(value: int | float | str, unit: str = "ms") -> datetime:
    if isinstance(value, str):
        value = float(value)

    if unit == "ms":
        value = value / 1000
    elif unit == "s":
        pass
    else:
        raise ValueError(f"Unknown time unit: {unit}")

    return datetime.fromtimestamp(value, tz=UTC)
