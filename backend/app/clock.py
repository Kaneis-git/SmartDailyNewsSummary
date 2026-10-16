from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def iso(value: datetime | None) -> str | None:
    return value.replace(tzinfo=UTC).isoformat() if value else None


def window(day: date, settings) -> tuple[datetime, datetime]:
    end = datetime.combine(day, time(settings.report_hour, settings.report_minute), ZoneInfo(settings.timezone))
    return ((end - timedelta(days=1)).astimezone(UTC).replace(tzinfo=None),
            end.astimezone(UTC).replace(tzinfo=None))


def local_now(settings) -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def due_today(settings) -> date | None:
    current = local_now(settings)
    return current.date() if (current.hour, current.minute) >= (settings.report_hour, settings.report_minute) else None
