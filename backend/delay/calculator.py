"""Compute delay = predicted (realtime) time - scheduled (static) time.

MTA's own GTFS-RT feed always reports `arrival.delay = 0` / `departure.delay =
0` — it doesn't fill those fields in. So "the delay" has to be derived
ourselves from the gap between what the realtime feed predicts and what the
static timetable scheduled, which is the whole point of this project.
"""
from __future__ import annotations

import datetime as dt

from backend.config import NY_TZ
from backend.delay.models import ScheduleIndex


def scheduled_epoch_seconds(
    index: ScheduleIndex, static_trip_id: str, stop_id: str, start_date: dt.date
) -> int | None:
    """The scheduled arrival time at `stop_id`, as a Unix timestamp.

    GTFS allows arrival_time past 24:00:00 for trips that run past midnight,
    so we add seconds-since-midnight to local midnight rather than parsing a
    wall-clock time directly.
    """
    seconds = index.stop_times.get(static_trip_id, {}).get(stop_id)
    if seconds is None:
        return None
    midnight = dt.datetime(start_date.year, start_date.month, start_date.day, tzinfo=NY_TZ)
    return int((midnight + dt.timedelta(seconds=seconds)).timestamp())


def delay_seconds(predicted_epoch: int, scheduled_epoch: int) -> int:
    """Positive = late, negative = early/ahead of schedule."""
    return predicted_epoch - scheduled_epoch
