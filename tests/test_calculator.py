import datetime as dt

from backend.delay.calculator import delay_seconds, scheduled_epoch_seconds
from backend.delay.models import ScheduleIndex


def test_scheduled_epoch_seconds_converts_time_of_day_to_unix_time():
    index = ScheduleIndex()
    index.stop_times["trip-1"] = {"137S": 7 * 3600 + 58 * 60 + 50}  # 07:58:50

    epoch = scheduled_epoch_seconds(index, "trip-1", "137S", dt.date(2026, 10, 19))

    from backend.config import NY_TZ
    expected = dt.datetime(2026, 10, 19, 7, 58, 50, tzinfo=NY_TZ)
    assert epoch == int(expected.timestamp())


def test_scheduled_epoch_seconds_handles_past_midnight_times():
    # GTFS allows e.g. "25:10:00" for a trip that departs at 1:10 AM the next day.
    index = ScheduleIndex()
    index.stop_times["trip-1"] = {"137S": 25 * 3600 + 10 * 60}

    epoch = scheduled_epoch_seconds(index, "trip-1", "137S", dt.date(2026, 10, 19))

    from backend.config import NY_TZ
    expected = dt.datetime(2026, 10, 20, 1, 10, 0, tzinfo=NY_TZ)
    assert epoch == int(expected.timestamp())


def test_scheduled_epoch_seconds_returns_none_when_unknown():
    index = ScheduleIndex()
    assert scheduled_epoch_seconds(index, "trip-1", "137S", dt.date(2026, 10, 19)) is None


def test_delay_seconds_positive_means_late():
    assert delay_seconds(predicted_epoch=1000, scheduled_epoch=700) == 300


def test_delay_seconds_negative_means_early():
    assert delay_seconds(predicted_epoch=700, scheduled_epoch=1000) == -300
