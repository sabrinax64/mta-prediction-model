"""Turn a decoded GTFS-RT feed into the flat list of per-train delay
observations the rest of the system (storage, REST, WebSocket, map) consumes.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backend.delay.calculator import delay_seconds, scheduled_epoch_seconds
from backend.delay.matcher import find_static_trip
from backend.delay.models import ScheduleIndex


@dataclass
class TrainObservation:
    observed_at: int  # unix epoch, when we polled the feed
    route_id: str
    trip_id: str  # realtime trip_id
    direction: str  # "N" or "S", parsed off the trip_id's path suffix
    current_stop_id: str
    stop_name: str | None
    lat: float | None
    lon: float | None
    predicted_epoch: int
    delay_seconds: int | None  # None if we couldn't match a static trip/stop


def _direction_from_trip_id(realtime_trip_id: str) -> str:
    # e.g. "079850_1..S15R" -> the path segment "S15R" starts with N or S.
    tail = realtime_trip_id.rsplit("..", 1)[-1]
    return tail[0] if tail else "?"


def build_observations(
    index: ScheduleIndex,
    feed_entities,  # iterable of gtfs_realtime_pb2 FeedEntity with trip_update set
    observed_at: int,
) -> list[TrainObservation]:
    observations = []

    for entity in feed_entities:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        trip = tu.trip
        try:
            start_date = dt.datetime.strptime(trip.start_date, "%Y%m%d").date()
        except ValueError:
            continue

        static_trip = find_static_trip(index, trip.trip_id, trip.route_id, start_date)

        # Use the *next* stop this train hasn't passed yet as "current" —
        # good enough for a live map since GTFS-RT subway feeds don't carry
        # vehicle lat/lon, only stop_id + status (see README).
        stop_time_updates = list(tu.stop_time_update)
        if not stop_time_updates:
            continue
        next_update = stop_time_updates[0]
        stop_id = next_update.stop_id
        if next_update.HasField("arrival"):
            predicted_epoch = next_update.arrival.time
        elif next_update.HasField("departure"):
            predicted_epoch = next_update.departure.time
        else:
            continue

        delay = None
        if static_trip is not None:
            sched_epoch = scheduled_epoch_seconds(index, static_trip.trip_id, stop_id, start_date)
            if sched_epoch is not None:
                delay = delay_seconds(predicted_epoch, sched_epoch)

        lat = lon = None
        stop_name = None
        stop_info = index.stops.get(stop_id)
        if stop_info is not None:
            lat, lon, stop_name = stop_info

        observations.append(
            TrainObservation(
                observed_at=observed_at,
                route_id=trip.route_id,
                trip_id=trip.trip_id,
                direction=_direction_from_trip_id(trip.trip_id),
                current_stop_id=stop_id,
                stop_name=stop_name,
                lat=lat,
                lon=lon,
                predicted_epoch=predicted_epoch,
                delay_seconds=delay,
            )
        )

    return observations
