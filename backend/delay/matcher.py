"""Match a GTFS-Realtime trip_id to the static-schedule trip it corresponds to.

MTA's realtime trip_id (e.g. "079850_1..S15R") is NOT the same string as the
static GTFS trip_id (e.g. "XL0S1-1-1094-S02_079850_1..S15R") — it's missing the
service/shape prefix. But it IS always an exact suffix of the static trip_id:
static_trip_id == f"{some_prefix}_{realtime_trip_id}".

So matching is exact, not fuzzy: index static trips by that suffix, then
disambiguate by (a) route_id and (b) which service_id is actually running on
the realtime trip's start_date. Confirmed against the live feed in
development — see project README for how this was verified.
"""
from __future__ import annotations

import datetime as dt

from backend.delay.models import ScheduleIndex, StaticTrip


def find_static_trip(
    index: ScheduleIndex,
    realtime_trip_id: str,
    route_id: str,
    start_date: dt.date,
) -> StaticTrip | None:
    candidates = index.trips_by_suffix.get(realtime_trip_id)
    if not candidates:
        return None

    active_services = index.active_service_ids(start_date)
    matches = [
        t for t in candidates
        if t.route_id == route_id and t.service_id in active_services
    ]
    if not matches:
        return None
    # In practice this is unique; if more than one service is simultaneously
    # active for the same suffix+route (e.g. a holiday override), prefer the
    # first — good enough for the scaffold, revisit if you see it happen.
    return matches[0]
