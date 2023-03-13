from datetime import datetime, timezone

A_HOUR = 3600
A_DAY = 24 * A_HOUR
A_WEEK = 7 * A_DAY


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)
