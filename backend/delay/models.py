"""In-memory representation of the static GTFS schedule.

This is rebuilt whenever the static feed is (re)loaded (see
backend/gtfs_static/load.py) and held in memory by the ingestion service so
every 30s poll can match+diff against it without hitting Postgres per stop.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StaticTrip:
    trip_id: str
    route_id: str
    service_id: str
    direction_id: str


@dataclass(frozen=True)
class Service:
    service_id: str
    weekdays: frozenset  # set of int, 0=Monday .. 6=Sunday
    start_date: dt.date
    end_date: dt.date
    added_dates: frozenset = field(default_factory=frozenset)
    removed_dates: frozenset = field(default_factory=frozenset)

    def active_on(self, date: dt.date) -> bool:
        if date in self.removed_dates:
            return False
        if date in self.added_dates:
            return True
        return (
            self.start_date <= date <= self.end_date
            and date.weekday() in self.weekdays
        )


@dataclass
class ScheduleIndex:
    """Everything the live matcher/calculator need, keyed for O(1) lookups."""

    # realtime trip_id (== suffix of static trip_id after the first "_") -> candidates
    trips_by_suffix: dict[str, list[StaticTrip]] = field(default_factory=lambda: defaultdict(list))
    # static trip_id -> {stop_id: arrival_seconds_since_midnight}
    stop_times: dict[str, dict[str, int]] = field(default_factory=dict)
    # service_id -> Service
    services: dict[str, Service] = field(default_factory=dict)
    # stop_id -> (lat, lon, name)
    stops: dict[str, tuple] = field(default_factory=dict)

    def active_service_ids(self, date: dt.date) -> set:
        return {sid for sid, svc in self.services.items() if svc.active_on(date)}
